import { useEffect, useState } from "react";
import { BrowserRouter, Route, Routes, useNavigate } from "react-router-dom";
import { getJson, postEmpty } from "./api";
import Navbar from "./components/Navbar";
import CreateRecord from "./pages/CreateRecord";
import DeleteRecord from "./pages/DeleteRecord";
import Home from "./pages/Home";
import Login from "./pages/Login";
import UpdateRecord from "./pages/UpdateRecord";

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
            <Route path="/create" element={<CreateRecord onAdd={handleAdd} />} />
            <Route path="/update" element={<UpdateRecord onUpdate={handleUpdate} />} />
            <Route path="/update/:id" element={<UpdateRecord onUpdate={handleUpdate} />} />
            <Route path="/delete" element={<DeleteRecord onDelete={handleDelete} />} />
            <Route path="/delete/:id" element={<DeleteRecord onDelete={handleDelete} />} />
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
