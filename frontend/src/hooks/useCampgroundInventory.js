import { useState, useEffect, useCallback } from 'react';
import {
  collection,
  query,
  where,
  orderBy,
  limit,
  startAfter,
  getDocs,
  getCountFromServer,
} from 'firebase/firestore';
import { db } from '../config/firebase';

const PAGE_SIZE = 25;
const ALL_SOURCES = [
  'recreation_gov', 'nps', 'koa', 'hipcamp',
  'good_sam', 'thousand_trails', 'state_parks',
];

/**
 * Hook that provides inventory statistics and a paginated campground list.
 *
 * @param {{ source?: string, state?: string }} filters
 */
export function useCampgroundInventory(filters = {}) {
  const [stats, setStats] = useState(null);
  const [campgrounds, setCampgrounds] = useState([]);
  const [loading, setLoading] = useState(true);
  const [listLoading, setListLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastDoc, setLastDoc] = useState(null);
  const [hasMore, setHasMore] = useState(true);

  // Fetch aggregate stats (total + per-source counts)
  useEffect(() => {
    let cancelled = false;

    async function fetchStats() {
      try {
        const campRef = collection(db, 'campgrounds');

        // Total count
        const totalSnap = await getCountFromServer(query(campRef));
        const total = totalSnap.data().count;

        // Per-source counts
        const sourceCounts = {};
        await Promise.all(
          ALL_SOURCES.map(async (src) => {
            const snap = await getCountFromServer(
              query(campRef, where('source', '==', src))
            );
            sourceCounts[src] = snap.data().count;
          })
        );

        if (!cancelled) {
          setStats({ total, sourceCounts });
        }
      } catch (err) {
        if (!cancelled) setError(err);
      }
    }

    fetchStats();
    return () => { cancelled = true; };
  }, []);

  // Fetch paginated campground list
  useEffect(() => {
    let cancelled = false;

    async function fetchList() {
      setLoading(true);
      setError(null);

      try {
        const campRef = collection(db, 'campgrounds');
        const constraints = [];

        if (filters.source) {
          constraints.push(where('source', '==', filters.source));
        }
        if (filters.state) {
          constraints.push(where('location.state', '==', filters.state));
        }

        constraints.push(orderBy('name'));
        constraints.push(limit(PAGE_SIZE));

        const q = query(campRef, ...constraints);
        const snapshot = await getDocs(q);

        if (cancelled) return;

        const docs = snapshot.docs.map((doc) => ({
          id: doc.id,
          ...doc.data(),
        }));

        setCampgrounds(docs);
        setLastDoc(snapshot.docs[snapshot.docs.length - 1] || null);
        setHasMore(snapshot.docs.length >= PAGE_SIZE);
      } catch (err) {
        if (!cancelled) setError(err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchList();
    return () => { cancelled = true; };
  }, [filters.source, filters.state]);

  const loadMore = useCallback(async () => {
    if (listLoading || !hasMore || !lastDoc) return;

    setListLoading(true);

    try {
      const campRef = collection(db, 'campgrounds');
      const constraints = [];

      if (filters.source) {
        constraints.push(where('source', '==', filters.source));
      }
      if (filters.state) {
        constraints.push(where('location.state', '==', filters.state));
      }

      constraints.push(orderBy('name'));
      constraints.push(startAfter(lastDoc));
      constraints.push(limit(PAGE_SIZE));

      const q = query(campRef, ...constraints);
      const snapshot = await getDocs(q);

      const docs = snapshot.docs.map((doc) => ({
        id: doc.id,
        ...doc.data(),
      }));

      setCampgrounds((prev) => [...prev, ...docs]);
      setLastDoc(snapshot.docs[snapshot.docs.length - 1] || null);
      setHasMore(snapshot.docs.length >= PAGE_SIZE);
    } catch (err) {
      setError(err);
    } finally {
      setListLoading(false);
    }
  }, [listLoading, hasMore, lastDoc, filters.source, filters.state]);

  return { stats, campgrounds, loading, listLoading, error, loadMore, hasMore };
}
