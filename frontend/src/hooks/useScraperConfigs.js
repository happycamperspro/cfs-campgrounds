import { useState, useEffect, useCallback } from 'react';
import { collection, doc, onSnapshot, updateDoc } from 'firebase/firestore';
import { db } from '../config/firebase';

/**
 * Hook that maintains a realtime listener on the `_scraper_configs` collection.
 * Returns configs as an array, plus helper functions for toggling and updating.
 *
 * @returns {{ configs: array, loading: boolean, error: Error|null, toggleEnabled: Function, updateConfig: Function }}
 */
export function useScraperConfigs() {
  const [configs, setConfigs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const configsRef = collection(db, '_scraper_configs');

    const unsubscribe = onSnapshot(
      configsRef,
      (snapshot) => {
        const result = snapshot.docs.map((d) => ({
          id: d.id,
          name: d.id,
          ...d.data(),
        }));
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

  const toggleEnabled = useCallback(async (spiderName) => {
    const config = configs.find((c) => c.name === spiderName);
    if (!config) return;
    const configRef = doc(db, '_scraper_configs', spiderName);
    await updateDoc(configRef, { enabled: !config.enabled });
  }, [configs]);

  const updateConfig = useCallback(async (spiderName, data) => {
    const configRef = doc(db, '_scraper_configs', spiderName);
    await updateDoc(configRef, data);
  }, []);

  return { configs, loading, error, toggleEnabled, updateConfig };
}
