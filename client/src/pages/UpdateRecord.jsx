import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { getJson, sendJson } from "../api";

function UpdateRecord({ onUpdate }) {
  const { id } = useParams();
  const [propertyTitle, setPropertyTitle] = useState("");
  const [location, setLocation] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    if (!id) {
      return;
    }
    getJson("/api/listings/" + id)
      .then((data) => {
        setPropertyTitle(data.property_title);
        setLocation(data.location);
      })
      .catch((err) => setError(err.message));
  }, [id]);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    try {
      const updatedListing = await sendJson("/api/listings/" + id, "PUT", {
        property_title: propertyTitle,
        location,
      });
      onUpdate(updatedListing);
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
      <h1>Update Listing</h1>
      <form onSubmit={handleSubmit}>
        {error ? <p className="error">{error}</p> : null}
        <div className="field">
          <label htmlFor="property-title">Property Title</label>
          <input
            id="property-title"
            value={propertyTitle}
            onChange={(event) => setPropertyTitle(event.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="location">Location</label>
          <input
            id="location"
            value={location}
            onChange={(event) => setLocation(event.target.value)}
          />
        </div>
        <button className="btn primary" type="submit">
          Update Listing
        </button>
      </form>
    </section>
  );
}

export default UpdateRecord;
