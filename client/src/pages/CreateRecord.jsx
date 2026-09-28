import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { sendJson } from "../api";

function CreateRecord({ onAdd }) {
  const [propertyTitle, setPropertyTitle] = useState("");
  const [location, setLocation] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    try {
      const createdListing = await sendJson("/api/listings", "POST", {
        property_title: propertyTitle,
        location,
      });
      onAdd(createdListing);
      navigate("/");
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section className="card form-card">
      <h1>Add Listing</h1>
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
          Add Listing
        </button>
      </form>
    </section>
  );
}

export default CreateRecord;
