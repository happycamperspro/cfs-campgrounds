import { Link } from 'react-router-dom';
import { REGIONS } from '../../lib/constants';

const regionKeys = Object.keys(REGIONS);

export default function Footer() {
  return (
    <footer className="bg-gray-900 text-gray-300">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Brand */}
          <div>
            <Link to="/" className="flex items-center gap-2 mb-4">
              <svg
                className="h-7 w-7 text-campfire-500"
                viewBox="0 0 24 24"
                fill="currentColor"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path d="M12 2C10.5 5 7 8 7 11.5C7 14.5 9.2 17 12 17C14.8 17 17 14.5 17 11.5C17 8 13.5 5 12 2Z" />
                <rect x="8" y="17" width="8" height="2" rx="1" />
              </svg>
              <span className="text-lg font-bold text-white">
                Camp<span className="text-campfire-500">fire</span>
              </span>
            </Link>
            <p className="text-sm text-gray-400 leading-relaxed">
              Discover and explore campgrounds across the United States. Your next outdoor
              adventure starts here.
            </p>
          </div>

          {/* Quick links */}
          <div>
            <h3 className="text-white font-semibold mb-3 text-sm uppercase tracking-wider">
              Explore
            </h3>
            <ul className="space-y-2">
              <li>
                <Link to="/browse" className="text-sm hover:text-campfire-400 transition-colors">
                  Browse All
                </Link>
              </li>
              <li>
                <Link to="/map" className="text-sm hover:text-campfire-400 transition-colors">
                  Map View
                </Link>
              </li>
            </ul>
          </div>

          {/* Region links */}
          <div>
            <h3 className="text-white font-semibold mb-3 text-sm uppercase tracking-wider">
              Browse by Region
            </h3>
            <ul className="space-y-2">
              {regionKeys.map((region) => (
                <li key={region}>
                  <Link
                    to={`/browse?region=${encodeURIComponent(region)}`}
                    className="text-sm hover:text-campfire-400 transition-colors"
                  >
                    {region}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="mt-10 pt-8 border-t border-gray-800 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-xs text-gray-500">
            Powered by Recreation.gov, NPS, and community data.
          </p>
          <p className="text-xs text-gray-500">
            &copy; {new Date().getFullYear()} Campfire Campgrounds. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
}
