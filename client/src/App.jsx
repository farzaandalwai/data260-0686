import { useEffect, useState } from "react";
import { BrowserRouter, Link, Route, Routes, useNavigate } from "react-router-dom";
import { getJson, postEmpty } from "./api";
import Navbar from "./components/Navbar";
import CreateRecord from "./pages/CreateRecord";
import DeleteRecord from "./pages/DeleteRecord";
import Home from "./pages/Home";
import Login from "./pages/Login";
import UpdateRecord from "./pages/UpdateRecord";
import { useDispatch } from "react-redux";
import { clearListings } from "./features/listings/listingsSlice";

function LoginRequired() {
  return (
    <section className="card">
      <h1>Login required</h1>
      <p>Sign in to view rental listings.</p>
      <Link className="btn primary" to="/login">
        Go to Login
      </Link>
    </section>
  );
}

function AppShell() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const dispatch = useDispatch();
  const navigate = useNavigate();

  useEffect(() => {
    getJson("/api/auth/me")
      .then((data) => setUser(data))
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  async function handleLogout() {
    await postEmpty("/api/auth/logout");
    setUser(null);
    dispatch(clearListings());
    navigate("/login");
  }

  return (
    <>
      <Navbar user={user} onLogout={handleLogout} />
      <main className="page">
        {loading ? (
          <p>Loading...</p>
        ) : (
          <Routes>
            <Route
              path="/"
              element={<Home user={user} />}
            />
            <Route path="/login" element={<Login setUser={setUser} />} />
            <Route
              path="/create"
              element={user ? <CreateRecord /> : <LoginRequired />}
            />
            <Route
              path="/update"
              element={user ? <UpdateRecord /> : <LoginRequired />}
            />
            <Route
              path="/update/:id"
              element={user ? <UpdateRecord /> : <LoginRequired />}
            />
            <Route
              path="/delete"
              element={user ? <DeleteRecord /> : <LoginRequired />}
            />
            <Route
              path="/delete/:id"
              element={user ? <DeleteRecord /> : <LoginRequired />}
            />
          </Routes>
        )}
      </main>
    </>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AppShell />
    </BrowserRouter>
  );
}

export default App;
