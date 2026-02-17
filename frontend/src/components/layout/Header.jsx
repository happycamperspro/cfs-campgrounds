import { useState } from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import { signOut } from 'firebase/auth';
import { useAuthContext } from '../../context/AuthContext';
import { auth } from '../../config/firebase';
import SearchBar from '../search/SearchBar';

const navLinks = [
  { to: '/browse', label: 'Browse' },
  { to: '/map', label: 'Map' },
];

export default function Header() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { user, isSuperAdmin } = useAuthContext();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await signOut(auth);
    navigate('/');
  };

  return (
    <header className="sticky top-0 z-50 bg-white border-b border-gray-200 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2 flex-shrink-0">
            <svg
              className="h-8 w-8 text-campfire-500"
              viewBox="0 0 24 24"
              fill="currentColor"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path d="M12 2C10.5 5 7 8 7 11.5C7 14.5 9.2 17 12 17C14.8 17 17 14.5 17 11.5C17 8 13.5 5 12 2Z" />
              <path
                d="M12 6C11.2 8 9.5 9.5 9.5 11.5C9.5 13.2 10.6 14.5 12 14.5C13.4 14.5 14.5 13.2 14.5 11.5C14.5 9.5 12.8 8 12 6Z"
                className="text-campfire-300"
                fill="currentColor"
              />
              <rect x="8" y="17" width="8" height="2" rx="1" />
              <rect x="9" y="19" width="6" height="1.5" rx="0.75" />
            </svg>
            <span className="text-xl font-bold text-gray-900">
              Camp<span className="text-campfire-500">fire</span>
            </span>
          </Link>

          {/* Desktop nav */}
          <nav className="hidden md:flex items-center gap-6">
            {navLinks.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                className={({ isActive }) =>
                  `text-sm font-medium transition-colors ${
                    isActive
                      ? 'text-campfire-600'
                      : 'text-gray-600 hover:text-campfire-500'
                  }`
                }
              >
                {link.label}
              </NavLink>
            ))}
          </nav>

          {/* Search bar - desktop */}
          <div className="hidden md:block flex-1 max-w-md mx-6">
            <SearchBar />
          </div>

          {/* Admin link + Logout */}
          <div className="hidden md:flex items-center gap-4">
            <NavLink
              to={user && isSuperAdmin ? '/admin' : '/admin/login'}
              className={({ isActive }) =>
                `text-sm font-medium transition-colors ${
                  isActive
                    ? 'text-campfire-600'
                    : 'text-gray-600 hover:text-campfire-500'
                }`
              }
            >
              Admin
            </NavLink>
            {user && (
              <button
                type="button"
                onClick={handleLogout}
                className="text-sm font-medium text-gray-500 hover:text-red-600 transition-colors"
              >
                Logout
              </button>
            )}
          </div>

          {/* Mobile hamburger */}
          <button
            type="button"
            className="md:hidden inline-flex items-center justify-center p-2 rounded-md text-gray-500 hover:text-gray-700 hover:bg-gray-100 transition-colors"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label="Toggle menu"
          >
            {mobileMenuOpen ? (
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            ) : (
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            )}
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-gray-200 bg-white">
          <div className="px-4 py-3">
            <SearchBar onSearch={() => setMobileMenuOpen(false)} />
          </div>
          <nav className="px-4 pb-4 space-y-1">
            {navLinks.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                onClick={() => setMobileMenuOpen(false)}
                className={({ isActive }) =>
                  `block px-3 py-2 rounded-md text-base font-medium transition-colors ${
                    isActive
                      ? 'bg-campfire-50 text-campfire-600'
                      : 'text-gray-600 hover:bg-gray-50 hover:text-campfire-500'
                  }`
                }
              >
                {link.label}
              </NavLink>
            ))}
            <NavLink
              to={user && isSuperAdmin ? '/admin' : '/admin/login'}
              onClick={() => setMobileMenuOpen(false)}
              className={({ isActive }) =>
                `block px-3 py-2 rounded-md text-base font-medium transition-colors ${
                  isActive
                    ? 'bg-campfire-50 text-campfire-600'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-campfire-500'
                }`
              }
            >
              Admin
            </NavLink>
            {user && (
              <button
                type="button"
                onClick={() => { handleLogout(); setMobileMenuOpen(false); }}
                className="block w-full text-left px-3 py-2 rounded-md text-base font-medium text-gray-600 hover:bg-red-50 hover:text-red-600 transition-colors"
              >
                Logout
              </button>
            )}
          </nav>
        </div>
      )}
    </header>
  );
}
