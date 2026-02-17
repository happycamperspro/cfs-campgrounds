import { useState, useEffect } from 'react';
import { getDocs } from 'firebase/firestore';

/**
 * Generic hook that executes a Firestore query and returns the results.
 *
 * @param {Function} queryFn - A function that returns a Firestore Query, or null to skip.
 * @param {Array}    deps    - Dependency array that controls when the query re-runs.
 * @returns {{ data: Array, loading: boolean, error: Error|null, lastDoc: DocumentSnapshot|null }}
 */
export function useFirestore(queryFn, deps = []) {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastDoc, setLastDoc] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchData() {
      const q = queryFn();

      // If queryFn returns null, skip the fetch
      if (!q) {
        setData([]);
        setLoading(false);
        setLastDoc(null);
        return;
      }

      setLoading(true);
      setError(null);

      try {
        const snapshot = await getDocs(q);

        if (cancelled) return;

        const results = snapshot.docs.map((doc) => ({
          id: doc.id,
          ...doc.data(),
        }));

        setData(results);
        setLastDoc(snapshot.docs[snapshot.docs.length - 1] || null);
      } catch (err) {
        if (!cancelled) {
          setError(err);
          setData([]);
          setLastDoc(null);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    fetchData();

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return { data, loading, error, lastDoc };
}
