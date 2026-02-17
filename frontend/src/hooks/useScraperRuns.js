import { useState, useEffect, useCallback, useRef } from 'react';
import {
  collection,
  query,
  where,
  orderBy,
  limit,
  startAfter,
  getDocs,
  onSnapshot,
} from 'firebase/firestore';
import { db } from '../config/firebase';

const PAGE_SIZE = 20;

/**
 * Hook for reading scraper runs with optional filters and pagination.
 * Uses onSnapshot for active runs (status == "running" or "pending") to get
 * realtime updates, and getDocs for historical data.
 *
 * @param {{ spiderName?: string, status?: string }} filters
 * @returns {{ runs: Array, loading: boolean, error: Error|null, loadMore: Function, hasMore: boolean }}
 */
export function useScraperRuns({ spiderName, status } = {}) {
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastDoc, setLastDoc] = useState(null);
  const [hasMore, setHasMore] = useState(true);
  const activeUnsubRef = useRef(null);

  // Subscribe to active (running/pending) runs in realtime
  useEffect(() => {
    const runsRef = collection(db, '_scraper_runs');
    const constraints = [
      where('status', 'in', ['running', 'pending']),
      orderBy('startedAt', 'desc'),
    ];

    if (spiderName) {
      constraints.unshift(where('spiderName', '==', spiderName));
    }

    const q = query(runsRef, ...constraints);

    activeUnsubRef.current = onSnapshot(
      q,
      (snapshot) => {
        const activeRuns = snapshot.docs.map((doc) => ({
          id: doc.id,
          ...doc.data(),
          _isActive: true,
        }));

        setRuns((prev) => {
          // Merge: replace active runs at the front, keep completed runs after
          const completedRuns = prev.filter((r) => !r._isActive);
          return [...activeRuns, ...completedRuns];
        });
      },
      (err) => {
        setError(err);
      }
    );

    return () => {
      if (activeUnsubRef.current) {
        activeUnsubRef.current();
      }
    };
  }, [spiderName]);

  // Fetch historical / filtered runs (non-realtime)
  useEffect(() => {
    let cancelled = false;

    async function fetchRuns() {
      setLoading(true);
      setError(null);

      try {
        const runsRef = collection(db, '_scraper_runs');
        const constraints = [orderBy('startedAt', 'desc')];

        if (spiderName) {
          constraints.unshift(where('spiderName', '==', spiderName));
        }
        if (status) {
          constraints.unshift(where('status', '==', status));
        }

        constraints.push(limit(PAGE_SIZE));

        const q = query(runsRef, ...constraints);
        const snapshot = await getDocs(q);

        if (cancelled) return;

        const docs = snapshot.docs.map((doc) => ({
          id: doc.id,
          ...doc.data(),
        }));

        setRuns((prev) => {
          // Keep active (realtime) runs, replace historical
          const activeRuns = prev.filter((r) => r._isActive);
          return [...activeRuns, ...docs.filter((d) => !activeRuns.some((a) => a.id === d.id))];
        });
        setLastDoc(snapshot.docs[snapshot.docs.length - 1] || null);
        setHasMore(snapshot.docs.length >= PAGE_SIZE);
      } catch (err) {
        if (!cancelled) {
          setError(err);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    fetchRuns();

    return () => {
      cancelled = true;
    };
  }, [spiderName, status]);

  const loadMore = useCallback(async () => {
    if (loading || !hasMore || !lastDoc) return;

    setLoading(true);
    setError(null);

    try {
      const runsRef = collection(db, '_scraper_runs');
      const constraints = [orderBy('startedAt', 'desc')];

      if (spiderName) {
        constraints.unshift(where('spiderName', '==', spiderName));
      }
      if (status) {
        constraints.unshift(where('status', '==', status));
      }

      constraints.push(startAfter(lastDoc));
      constraints.push(limit(PAGE_SIZE));

      const q = query(runsRef, ...constraints);
      const snapshot = await getDocs(q);

      const docs = snapshot.docs.map((doc) => ({
        id: doc.id,
        ...doc.data(),
      }));

      setRuns((prev) => [...prev, ...docs]);
      setLastDoc(snapshot.docs[snapshot.docs.length - 1] || null);
      setHasMore(snapshot.docs.length >= PAGE_SIZE);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [loading, hasMore, lastDoc, spiderName, status]);

  return { runs, loading, error, loadMore, hasMore };
}
