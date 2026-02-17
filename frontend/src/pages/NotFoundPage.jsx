import { Link } from 'react-router-dom';

export default function NotFoundPage() {
  return (
    <div className="min-h-[60vh] flex items-center justify-center px-4">
      <div className="text-center max-w-md">
        <h1 className="text-7xl font-extrabold text-campfire-500 mb-4">404</h1>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Page Not Found</h2>
        <p className="text-gray-600 mb-8">
          Looks like you&apos;ve wandered off the trail. The page you&apos;re looking for
          doesn&apos;t exist or has been moved.
        </p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
          <Link to="/" className="btn-primary px-6">
            Go Home
          </Link>
          <Link to="/browse" className="btn-outline px-6">
            Browse Campgrounds
          </Link>
        </div>
      </div>
    </div>
  );
}
