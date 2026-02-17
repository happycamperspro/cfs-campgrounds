import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { collection, query, limit, orderBy, getDocs } from 'firebase/firestore';
import { db } from '../config/firebase';
import { REGIONS, US_STATES } from '../lib/constants';
import { truncate, formatRating } from '../lib/utils';
import SearchBar from '../components/search/SearchBar';
import LoadingSpinner from '../components/ui/LoadingSpinner';

export default function HomePage() {
  const [featured, setFeatured] = useState([]);
  const [loadingFeatured, setLoadingFeatured] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    async function loadFeatured() {
      try {
        const q = query(
          collection(db, 'campgrounds'),
          orderBy('rating.average', 'desc'),
          limit(6)
        );
        const snapshot = await getDocs(q);
        const campgrounds = snapshot.docs.map((doc) => ({
          id: doc.id,
          ...doc.data(),
        }));
        setFeatured(campgrounds);
      } catch (err) {
        console.error('Failed to load featured campgrounds:', err);
      } finally {
        setLoadingFeatured(false);
      }
    }
    loadFeatured();
  }, []);

  const stateAbbreviations = Object.keys(US_STATES);

  return (
    <div>
      {/* Hero Section */}
      <section className="relative bg-gradient-to-br from-forest-900 via-forest-800 to-forest-950 text-white">
        <div className="absolute inset-0 bg-black/20" />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 sm:py-28 lg:py-36">
          <div className="text-center max-w-3xl mx-auto">
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight mb-6">
              Discover Your Perfect{' '}
              <span className="text-campfire-400">Campground</span>
            </h1>
            <p className="text-lg sm:text-xl text-gray-200 mb-10 leading-relaxed">
              Explore thousands of campgrounds across the United States. From national
              parks to hidden gems, find your next outdoor adventure.
            </p>
            <div className="max-w-lg mx-auto">
              <SearchBar
                variant="hero"
                onSearch={() => {}}
                placeholder="Search campgrounds, parks, or states..."
              />
            </div>
            <div className="mt-8 flex flex-wrap justify-center gap-3">
              <Link to="/browse" className="btn-primary text-lg px-6 py-3">
                Browse All Campgrounds
              </Link>
              <Link to="/map" className="btn-outline border-white text-white hover:bg-white/10 text-lg px-6 py-3">
                View Map
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Featured Campgrounds */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="text-center mb-10">
          <h2 className="text-3xl font-bold text-gray-900">Featured Campgrounds</h2>
          <p className="mt-2 text-gray-600">Top-rated campgrounds loved by outdoor enthusiasts</p>
        </div>

        {loadingFeatured ? (
          <div className="flex justify-center py-12">
            <LoadingSpinner size="lg" />
          </div>
        ) : featured.length === 0 ? (
          <p className="text-center text-gray-500 py-12">
            No campgrounds found yet. Check back soon!
          </p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {featured.map((cg) => (
              <Link
                key={cg.id}
                to={`/campground/${cg.slug || cg.id}`}
                className="card group"
              >
                <div className="aspect-[4/3] bg-gray-200 overflow-hidden">
                  {cg.images && cg.images.length > 0 ? (
                    <img
                      src={cg.images[0]}
                      alt={cg.name}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                      loading="lazy"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-forest-100 to-forest-200">
                      <svg className="h-16 w-16 text-forest-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 21h18M5 21V7l7-4 7 4v14" />
                      </svg>
                    </div>
                  )}
                </div>
                <div className="p-4">
                  <h3 className="font-semibold text-gray-900 group-hover:text-campfire-600 transition-colors">
                    {cg.name}
                  </h3>
                  <p className="text-sm text-gray-500 mt-1">
                    {cg.city && `${cg.city}, `}
                    {cg.state && US_STATES[cg.state]}
                  </p>
                  {cg.rating?.average > 0 && (
                    <div className="flex items-center gap-1 mt-2">
                      <svg className="h-4 w-4 text-campfire-500" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                      </svg>
                      <span className="text-sm font-medium text-gray-700">
                        {formatRating(cg.rating.average, cg.rating.count)}
                      </span>
                    </div>
                  )}
                  {cg.description && (
                    <p className="text-sm text-gray-500 mt-2 line-clamp-2">
                      {truncate(cg.description, 120)}
                    </p>
                  )}
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>

      {/* Browse by Region */}
      <section className="bg-white py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-10">
            <h2 className="text-3xl font-bold text-gray-900">Browse by Region</h2>
            <p className="mt-2 text-gray-600">Explore campgrounds across different regions</p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {Object.entries(REGIONS).map(([region, states]) => (
              <Link
                key={region}
                to={`/browse?region=${encodeURIComponent(region)}`}
                className="group p-5 rounded-xl border border-gray-200 hover:border-campfire-300 hover:shadow-md transition-all bg-white"
              >
                <h3 className="font-semibold text-gray-900 group-hover:text-campfire-600 transition-colors">
                  {region}
                </h3>
                <p className="text-sm text-gray-500 mt-1">
                  {states.length} {states.length === 1 ? 'state' : 'states'}
                </p>
                <div className="mt-2 flex flex-wrap gap-1">
                  {states.slice(0, 5).map((st) => (
                    <span
                      key={st}
                      className="inline-block px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded"
                    >
                      {st}
                    </span>
                  ))}
                  {states.length > 5 && (
                    <span className="inline-block px-2 py-0.5 text-gray-400 text-xs">
                      +{states.length - 5} more
                    </span>
                  )}
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* Browse by State */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="text-center mb-10">
          <h2 className="text-3xl font-bold text-gray-900">Browse by State</h2>
          <p className="mt-2 text-gray-600">Jump directly to campgrounds in your state</p>
        </div>
        <div className="flex flex-wrap justify-center gap-2">
          {stateAbbreviations.map((abbr) => (
            <Link
              key={abbr}
              to={`/browse/${abbr}`}
              className="px-3 py-2 text-sm font-medium rounded-lg border border-gray-200 text-gray-700 hover:bg-campfire-50 hover:border-campfire-300 hover:text-campfire-700 transition-all"
              title={US_STATES[abbr]}
            >
              {abbr}
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
