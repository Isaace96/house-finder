import { Route, Routes, Link } from "react-router-dom";
import { LoginPage } from "./auth/LoginPage";
import { ProtectedRoute } from "./auth/ProtectedRoute";
import { useAuth } from "./auth/AuthProvider";
import { SearchesPage } from "./pages/SearchesPage";
import { ReviewPage } from "./pages/ReviewPage";

function Nav() {
  const { session, signOut } = useAuth();
  if (!session) return null;
  return (
    <header className="bg-white border-b">
      <div className="max-w-6xl mx-auto px-6 py-3 flex items-center gap-4">
        <Link to="/" className="text-lg font-bold">
          House Finder
        </Link>
        <div className="ml-auto flex items-center gap-3 text-sm text-slate-600">
          <span>{session.user.email}</span>
          <button onClick={signOut} className="px-3 py-1 rounded bg-slate-100 hover:bg-slate-200">
            Sign out
          </button>
        </div>
      </div>
    </header>
  );
}

export function App() {
  return (
    <>
      <Nav />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <SearchesPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/searches/:id/review"
          element={
            <ProtectedRoute>
              <ReviewPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/searches/:id/review/:bucket"
          element={
            <ProtectedRoute>
              <ReviewPage />
            </ProtectedRoute>
          }
        />
      </Routes>
    </>
  );
}
