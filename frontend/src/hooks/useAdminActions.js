import { useState, useCallback } from 'react';
import { auth } from '../config/firebase';

/**
 * Resolves the base URL for Cloud Functions.
 * Uses the VITE_FUNCTIONS_URL env var if set, otherwise falls back to the
 * default Firebase Functions URL pattern.
 */
function getFunctionsBaseUrl() {
  if (import.meta.env.VITE_FUNCTIONS_URL) {
    return import.meta.env.VITE_FUNCTIONS_URL;
  }
  const projectId = import.meta.env.VITE_FIREBASE_PROJECT_ID || 'hcp-social-chat-firebase-host';
  return `https://us-central1-${projectId}.cloudfunctions.net`;
}

/**
 * Makes an authenticated POST request to a Cloud Function.
 */
async function authenticatedPost(endpoint, body) {
  const currentUser = auth.currentUser;
  if (!currentUser) {
    throw new Error('User must be authenticated to perform admin actions');
  }

  const token = await currentUser.getIdToken();
  const baseUrl = getFunctionsBaseUrl();

  const response = await fetch(`${baseUrl}/${endpoint}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error || `Request failed with status ${response.status}`);
  }

  return response.json();
}

/**
 * Hook that wraps fetch calls to Cloud Functions for admin scraper operations.
 *
 * @returns {{
 *   triggerScraper: Function,
 *   cancelScraper: Function,
 *   updateConfig: Function,
 *   loading: boolean,
 *   error: Error|null
 * }}
 */
export function useAdminActions() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const triggerScraper = useCallback(async (spiderName, config = {}) => {
    setLoading(true);
    setError(null);

    try {
      const result = await authenticatedPost('trigger_scraper', {
        spiderName,
        config,
      });
      return result;
    } catch (err) {
      setError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const cancelScraper = useCallback(async (runId) => {
    setLoading(true);
    setError(null);

    try {
      const result = await authenticatedPost('cancel_scraper', { runId });
      return result;
    } catch (err) {
      setError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const updateConfig = useCallback(async (spiderName, config) => {
    setLoading(true);
    setError(null);

    try {
      const result = await authenticatedPost('update_scraper_config', {
        spiderName,
        config,
      });
      return result;
    } catch (err) {
      setError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return { triggerScraper, cancelScraper, updateConfig, loading, error };
}
