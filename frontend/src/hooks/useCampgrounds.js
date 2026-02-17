import { useState, useEffect, useCallback, useRef } from 'react';
import { getDocs } from 'firebase/firestore';
import { db } from '../config/firebase';
import { buildBrowseQuery } from '../lib/queries';
import { useFilters } from '../context/FilterContext';
import { PAGE_SIZE } from '../lib/constants';

/**
 * Applies client-side post-filters for criteria that Firestore can't handle
 * in a single query (multiple array-contains, boolean fields, etc.).
 */
function applyPostFilters(campgrounds, filters) {
  let results = campgrounds;

  // If siteType was used in the Firestore query, hookups need client-side filtering
  // If neither was used, both need client-side filtering for array membership
  if (filters.hookups.length > 0 && filters.siteTypes.length > 0) {
    // siteType was sent to Firestore; post-filter hookups
    results = results.filter((c) =>
      filters.hookups.every((h) => c.amenities?.hookups?.includes(h))
    );
  }

  // Additional siteTypes beyond the first (Firestore only handles one via array-contains)
  if (filters.siteTypes.length > 1) {
    results = results.filter((c) =>
      filters.siteTypes.every((st) => c.details?.siteTypes?.includes(st))
    );
  }

  // Additional hookups beyond the first when siteTypes is empty
  if (filters.siteTypes.length === 0 && filters.hookups.length > 1) {
    results = results.filter((c) =>
      filters.hookups.every((h) => c.amenities?.hookups?.includes(h))
    );
  }

  // Facilities
  if (filters.facilities.length > 0) {
    results = results.filter((c) =>
      filters.facilities.every((f) => c.amenities?.facilities?.includes(f))
    );
  }

  // Activities
  if (filters.activities.length > 0) {
    results = results.filter((c) =>
      filters.activities.every((a) => c.amenities?.activities?.includes(a))
    );
  }

  // Pets allowed
  if (filters.petsAllowed !== null) {
    results = results.filter((c) => c.amenities?.petsAllowed === filters.petsAllowed);
  }

  // Accessibility
  if (filters.accessible !== null) {
    results = results.filter((c) => c.amenities?.accessibility === filters.accessible);
  }

  // Managed by
  if (filters.managedBy) {
    results = results.filter((c) => c.details?.managedBy === filters.managedBy);
  }

  return results;
}

/**
 * Hook for fetching and paginating campgrounds based on the current FilterContext.
 */
export function useCampgrounds() {
  const filters = useFilters();
  const [campgrounds, setCampgrounds] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastDoc, setLastDoc] = useState(null);
  const [hasMore, setHasMore] = useState(true);

  // Track current filter version to discard stale responses
  const filterVersionRef = useRef(0);

  // Reset and fetch first page when filters change
  useEffect(() => {
    let cancelled = false;
    filterVersionRef.current += 1;
    const currentVersion = filterVersionRef.current;

    async function fetchFirstPage() {
      setLoading(true);
      setError(null);
      setCampgrounds([]);
      setLastDoc(null);
      setHasMore(true);

      try {
        const q = buildBrowseQuery(db, {
          state: filters.state,
          region: filters.region,
          siteType: filters.siteTypes[0] || null,
          hookup: filters.siteTypes.length === 0 ? filters.hookups[0] || null : null,
          sortBy: filters.sortBy,
          lastDoc: null,
          pageSize: PAGE_SIZE,
        });

        const snapshot = await getDocs(q);

        if (cancelled || currentVersion !== filterVersionRef.current) return;

        const docs = snapshot.docs.map((d) => ({ id: d.id, ...d.data() }));
        const filtered = applyPostFilters(docs, filters);

        setCampgrounds(filtered);
        setLastDoc(snapshot.docs[snapshot.docs.length - 1] || null);
        setHasMore(snapshot.docs.length >= PAGE_SIZE);
      } catch (err) {
        if (!cancelled && currentVersion === filterVersionRef.current) {
          setError(err);
        }
      } finally {
        if (!cancelled && currentVersion === filterVersionRef.current) {
          setLoading(false);
        }
      }
    }

    fetchFirstPage();

    return () => {
      cancelled = true;
    };
  }, [
    filters.state,
    filters.region,
    filters.siteTypes,
    filters.hookups,
    filters.facilities,
    filters.activities,
    filters.petsAllowed,
    filters.accessible,
    filters.managedBy,
    filters.sortBy,
  ]);

  const loadMore = useCallback(async () => {
    if (loading || !hasMore || !lastDoc) return;

    setLoading(true);
    setError(null);

    try {
      const q = buildBrowseQuery(db, {
        state: filters.state,
        region: filters.region,
        siteType: filters.siteTypes[0] || null,
        hookup: filters.siteTypes.length === 0 ? filters.hookups[0] || null : null,
        sortBy: filters.sortBy,
        lastDoc,
        pageSize: PAGE_SIZE,
      });

      const snapshot = await getDocs(q);
      const docs = snapshot.docs.map((d) => ({ id: d.id, ...d.data() }));
      const filtered = applyPostFilters(docs, filters);

      setCampgrounds((prev) => [...prev, ...filtered]);
      setLastDoc(snapshot.docs[snapshot.docs.length - 1] || null);
      setHasMore(snapshot.docs.length >= PAGE_SIZE);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [loading, hasMore, lastDoc, filters]);

  return { campgrounds, loading, error, loadMore, hasMore };
}
