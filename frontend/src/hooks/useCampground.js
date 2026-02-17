import { useState, useEffect } from 'react';
import { getDocs } from 'firebase/firestore';
import { db } from '../config/firebase';
import { buildSlugQuery } from '../lib/queries';

/**
 * Hook that fetches a single campground by its slug.
 *
 * @param {string} slug - The campground's URL-friendly slug.
 * @returns {{ campground: object|null, loading: boolean, error: Error|null }}
 */
export function useCampground(slug) {
  const [campground, setCampground] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchCampground() {
      if (!slug) {
        setCampground(null);
        setLoading(false);
        return;
      }

      setLoading(true);
      setError(null);

      try {
        const q = buildSlugQuery(db, slug);
        const snapshot = await getDocs(q);

        if (cancelled) return;

        if (snapshot.empty) {
          setCampground(null);
        } else {
          const doc = snapshot.docs[0];
          setCampground({ id: doc.id, ...doc.data() });
        }
      } catch (err) {
        if (!cancelled) {
          setError(err);
          setCampground(null);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    fetchCampground();

    return () => {
      cancelled = true;
    };
  }, [slug]);

  return { campground, loading, error };
}
