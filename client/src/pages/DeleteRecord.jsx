import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { getJson, sendJson } from "../api";

function DeleteRecord({ onDelete }) {
  const { id } = useParams();
  const [listing, setListing] = useState(null);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    if (!id) {
      return;
    }
    getJson("/api/listings/" + id)
      .then((data) => setListing(data))
      .catch((err) => setError(err.message));
  }, [id]);

  async function handleDelete() {
    setError("");
    try {
      await sendJson("/api/listings/" + id, "DELETE");
      onDelete(Number(id));
      navigate("/");
    } catch (err) {
      setError(err.message);
    }
  }

  if (!id) {
    return (
      <section className="card">
        <p>Select a listing from the home page.</p>
        <Link className="btn secondary" to="/">
          Back to Home
        </Link>
      </section>
    );
  }

  return (
    <section className="card form-card">
      <h1>Delete listing?</h1>
      {error ? <p className="error">{error}</p> : null}
      {listing ? (
        <>
          <p className="confirm-line">
            Property: {listing.property_title}
          </p>
          <p className="confirm-line">Location: {listing.location}</p>
        </>
      ) : (
        <p>Loading listing...</p>
      )}
      <div className="button-row">
        <button className="btn danger" type="button" onClick={handleDelete}>
          Delete Listing
        </button>
        <Link className="btn secondary" to="/">
          Cancel
        </Link>
      </div>
    </section>
  );
}

export default DeleteRecord;
