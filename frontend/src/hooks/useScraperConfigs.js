import { useState, useEffect } from 'react';
import { collection, onSnapshot } from 'firebase/firestore';
import { db } from '../config/firebase';

/**
 * Hook that maintains a realtime listener on the `_scraper_configs` collection.
 * Returns configs as an object keyed by spider name (document ID).
 *
 * @returns {{ configs: object, loading: boolean, error: Error|null }}
 */
export function useScraperConfigs() {
  const [configs, setConfigs] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const configsRef = collection(db, '_scraper_configs');

    const unsubscribe = onSnapshot(
      configsRef,
      (snapshot) => {
        const result = {};
        snapshot.docs.forEach((doc) => {
          result[doc.id] = { id: doc.id, ...doc.data() };
        });
        setConfigs(result);
        setLoading(false);
        setError(null);
      },
      (err) => {
        setError(err);
        setLoading(false);
      }
    );

    return () => unsubscribe();
  }, []);

  return { configs, loading, error };
}
