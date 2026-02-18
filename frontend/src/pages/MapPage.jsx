import { lazy, Suspense, useState, useEffect } from 'react';
import { collection, query, where, orderBy, limit, getDocs } from 'firebase/firestore';
import { db } from '../config/firebase';
import LoadingSpinner from '../components/ui/LoadingSpinner';

const CampgroundMap = lazy(() => import('../components/map/CampgroundMap'));

export default function MapPage() {
  const [campgrounds, setCampgrounds] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function fetchCampgrounds() {
      try {
        const q = query(
          collection(db, 'campgrounds'),
          where('metadata.isActive', '==', true),
          orderBy('name'),
          limit(500)
        );
        const snapshot = await getDocs(q);
        if (!cancelled) {
          setCampgrounds(
            snapshot.docs.map((doc) => ({ id: doc.id, ...doc.data() }))
          );
        }
      } catch (err) {
        console.error('Failed to load campgrounds for map:', err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchCampgrounds();
    return () => { cancelled = true; };
  }, []);

  return (
    <div className="flex flex-col" style={{ height: 'calc(100vh - 4rem)' }}>
      <div className="px-4 sm:px-6 lg:px-8 py-3 bg-white border-b border-gray-200">
        <h1 className="text-lg font-semibold text-gray-900">Campground Map</h1>
        <p className="text-sm text-gray-500">
          Explore campgrounds across the United States
          {!loading && ` — ${campgrounds.length} campgrounds loaded`}
        </p>
      </div>
      <div className="flex-1 relative">
        <Suspense
          fallback={
            <div className="absolute inset-0 flex items-center justify-center bg-gray-100">
              <LoadingSpinner size="lg" />
            </div>
          }
        >
          {loading ? (
            <div className="absolute inset-0 flex items-center justify-center bg-gray-100">
              <LoadingSpinner size="lg" />
            </div>
          ) : (
            <CampgroundMap campgrounds={campgrounds} />
          )}
        </Suspense>
      </div>
    </div>
  );
}
