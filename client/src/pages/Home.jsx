import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getJson } from "../api";

function Home({ user, listings, setListings }) {
  const [error, setError] = useState("");

  useEffect(() => {
    if (!user) {
      return;
    }
    getJson("/api/listings")
      .then((data) => setListings(data))
      .catch((err) => setError(err.message));
  }, [user, setListings]);

  if (!user) {
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

  return (
    <section>
      <div className="page-header">
        <div>
          <h1>Rental Housing Listings</h1>
          <p className="muted">Signed in as {user.name}</p>
        </div>
        <Link className="btn primary" to="/create">
          Add Listing
        </Link>
      </div>
      {error ? <p className="error">{error}</p> : null}
      {listings.length === 0 ? (
        <p className="empty">No listings yet.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Property Title</th>
                <th>Location</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {listings.map((listing) => (
                <tr key={listing.id}>
                  <td>{listing.id}</td>
                  <td>{listing.property_title}</td>
                  <td>{listing.location}</td>
                  <td>
                    <div className="actions">
                      <Link className="btn secondary" to={"/update/" + listing.id}>
                        Update
                      </Link>
                      <Link className="btn danger" to={"/delete/" + listing.id}>
                        Delete
                      </Link>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export default Home;
