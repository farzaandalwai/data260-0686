import { useEffect, useState } from "react";
import { BrowserRouter, Link, Route, Routes, useNavigate } from "react-router-dom";
import { getJson, postEmpty } from "./api";
import Navbar from "./components/Navbar";
import CreateRecord from "./pages/CreateRecord";
import DeleteRecord from "./pages/DeleteRecord";
import Home from "./pages/Home";
import Login from "./pages/Login";
import UpdateRecord from "./pages/UpdateRecord";

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
  const [listings, setListings] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    getJson("/api/auth/me")
      .then((data) => setUser(data))
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  function handleAdd(listing) {
    setListings((current) => [...current, listing]);
  }

  function handleUpdate(listing) {
    setListings((current) =>
      current.map((item) => (item.id === listing.id ? listing : item))
    );
  }

  function handleDelete(id) {
    setListings((current) => current.filter((item) => item.id !== id));
  }

  async function handleLogout() {
    await postEmpty("/api/auth/logout");
    setUser(null);
    setListings([]);
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
              element={<Home user={user} listings={listings} setListings={setListings} />}
            />
            <Route path="/login" element={<Login setUser={setUser} />} />
            <Route
              path="/create"
              element={user ? <CreateRecord onAdd={handleAdd} /> : <LoginRequired />}
            />
            <Route
              path="/update"
              element={user ? <UpdateRecord onUpdate={handleUpdate} /> : <LoginRequired />}
            />
            <Route
              path="/update/:id"
              element={user ? <UpdateRecord onUpdate={handleUpdate} /> : <LoginRequired />}
            />
            <Route
              path="/delete"
              element={user ? <DeleteRecord onDelete={handleDelete} /> : <LoginRequired />}
            />
            <Route
              path="/delete/:id"
              element={user ? <DeleteRecord onDelete={handleDelete} /> : <LoginRequired />}
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
