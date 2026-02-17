import { useState, useEffect, useRef } from 'react';
import { getDocs } from 'firebase/firestore';
import { db } from '../config/firebase';
import { buildSearchQuery } from '../lib/queries';

const DEBOUNCE_MS = 300;
const MAX_RESULTS = 8;

/**
 * Search hook with debounced prefix-range query on campground names.
 *
 * @returns {{ query: string, setQuery: Function, results: Array, loading: boolean }}
 */
export function useSearch() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const timerRef = useRef(null);
  const activeQueryRef = useRef('');

  useEffect(() => {
    // Clear any pending debounce timer
    if (timerRef.current) {
      clearTimeout(timerRef.current);
    }

    const trimmed = query.trim();

    // Clear results immediately when query is empty
    if (!trimmed) {
      setResults([]);
      setLoading(false);
      activeQueryRef.current = '';
      return;
    }

    setLoading(true);

    timerRef.current = setTimeout(async () => {
      // Avoid executing if the query has already changed
      activeQueryRef.current = trimmed;

      try {
        const q = buildSearchQuery(db, trimmed, MAX_RESULTS);
        const snapshot = await getDocs(q);

        // Only update if this is still the active query
        if (activeQueryRef.current === trimmed) {
          setResults(
            snapshot.docs.map((doc) => ({
              id: doc.id,
              ...doc.data(),
            }))
          );
        }
      } catch (err) {
        // Silently fail for search -- stale results are acceptable
        if (activeQueryRef.current === trimmed) {
          setResults([]);
        }
      } finally {
        if (activeQueryRef.current === trimmed) {
          setLoading(false);
        }
      }
    }, DEBOUNCE_MS);

    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
    };
  }, [query]);

  return { query, setQuery, results, loading };
}
