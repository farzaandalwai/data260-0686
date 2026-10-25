import { useEffect } from "react";
import { Link } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import { deleteListing, fetchListings } from "../features/listings/listingsSlice";

function Home({ user }) {
  const dispatch = useDispatch();
  const { items: listings, total, page, page_size: pageSize, status, error } = useSelector((state) => state.listings);

  useEffect(() => {
    if (!user) {
      return;
    }
    dispatch(fetchListings());
  }, [user, dispatch]);

  async function handleDelete(id) {
    try {
      await dispatch(deleteListing(id)).unwrap();
      await dispatch(fetchListings(listings.length === 1 && page > 1 ? page - 1 : page));
    } catch {
      return;
    }
  }

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
          <p className="muted">Signed in as {user.username} ({user.role})</p>
        </div>
        {user.role !== "reader" ? <Link className="btn primary" to="/create">Add Listing</Link> : null}
      </div>
      {error ? <p className="error">{error}</p> : null}
      {status === "loading" ? <p>Loading listings...</p> : null}
      {status !== "loading" && listings.length === 0 ? (
        <p className="empty">No listings yet.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Property Title</th>
                <th>Location</th>
                <th>Listing Code</th>
                <th>Available Units</th>
                <th>Manager ID</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {listings.map((listing) => (
                <tr key={listing.id}>
                  <td>{listing.id}</td>
                  <td>{listing.property_title}</td>
                  <td>{listing.location}</td>
                  <td>{listing.listing_code}</td>
                  <td>{listing.available_units}</td>
                  <td>{listing.property_manager_id}</td>
                  <td>
                    <div className="actions">
                      {user.role !== "reader" ? <Link className="btn secondary" to={"/update/" + listing.id}>Update</Link> : null}
                      {user.role === "moderator" ? <button className="btn danger" type="button" disabled={status === "loading"} onClick={() => handleDelete(listing.id)}>Delete</button> : null}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <div className="button-row">
        <button className="btn secondary" disabled={page <= 1 || status === "loading"} onClick={() => dispatch(fetchListings(page - 1))}>Previous</button>
        <span>Page {page} of {Math.max(1, Math.ceil(total / pageSize))} · {total} listings</span>
        <button className="btn secondary" disabled={page * pageSize >= total || status === "loading"} onClick={() => dispatch(fetchListings(page + 1))}>Next</button>
      </div>
    </section>
  );
}

export default Home;
