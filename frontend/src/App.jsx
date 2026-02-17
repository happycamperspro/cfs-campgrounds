import { Routes, Route } from 'react-router-dom';
import { lazy, Suspense } from 'react';
import Layout from './components/layout/Layout';
import HomePage from './pages/HomePage';
import LoadingSpinner from './components/ui/LoadingSpinner';
import AdminRoute from './components/admin/AdminRoute';

const BrowsePage = lazy(() => import('./pages/BrowsePage'));
const StatePage = lazy(() => import('./pages/StatePage'));
const CampgroundPage = lazy(() => import('./pages/CampgroundPage'));
const MapPage = lazy(() => import('./pages/MapPage'));
const NotFoundPage = lazy(() => import('./pages/NotFoundPage'));

// Admin pages
const AdminLoginPage = lazy(() => import('./pages/admin/AdminLoginPage'));
const DashboardPage = lazy(() => import('./pages/admin/DashboardPage'));
const ScrapersPage = lazy(() => import('./pages/admin/ScrapersPage'));
const SpiderDetailPage = lazy(() => import('./pages/admin/SpiderDetailPage'));
const RunHistoryPage = lazy(() => import('./pages/admin/RunHistoryPage'));
const InventoryPage = lazy(() => import('./pages/admin/InventoryPage'));

export default function App() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center">
          <LoadingSpinner size="lg" />
        </div>
      }
    >
      <Routes>
        <Route element={<Layout />}>
          {/* Public routes */}
          <Route path="/" element={<HomePage />} />
          <Route path="/browse" element={<BrowsePage />} />
          <Route path="/browse/:state" element={<StatePage />} />
          <Route path="/campground/:slug" element={<CampgroundPage />} />
          <Route path="/map" element={<MapPage />} />

          {/* Admin routes */}
          <Route path="/admin/login" element={<AdminLoginPage />} />
          <Route
            path="/admin"
            element={
              <AdminRoute>
                <DashboardPage />
              </AdminRoute>
            }
          />
          <Route
            path="/admin/scrapers"
            element={
              <AdminRoute>
                <ScrapersPage />
              </AdminRoute>
            }
          />
          <Route
            path="/admin/scrapers/:name"
            element={
              <AdminRoute>
                <SpiderDetailPage />
              </AdminRoute>
            }
          />
          <Route
            path="/admin/runs"
            element={
              <AdminRoute>
                <RunHistoryPage />
              </AdminRoute>
            }
          />
          <Route
            path="/admin/inventory"
            element={
              <AdminRoute>
                <InventoryPage />
              </AdminRoute>
            }
          />

          {/* 404 */}
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </Suspense>
  );
}
