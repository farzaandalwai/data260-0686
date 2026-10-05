import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import { updateListing } from "../features/listings/listingsSlice";
import api, { errorMessage, fetchManagers } from "../api/axios";

function UpdateRecord() {
  const { id } = useParams();
  const [propertyTitle, setPropertyTitle] = useState("");
  const [location, setLocation] = useState("");
  const [error, setError] = useState("");
  const [listingCode, setListingCode] = useState("");
  const [availableUnits, setAvailableUnits] = useState(1);
  const [managerId, setManagerId] = useState("");
  const [managers, setManagers] = useState([]);
  const [loadedId, setLoadedId] = useState("");
  const dispatch = useDispatch();
  const saving = useSelector((state) => state.listings.status === "loading");
  const navigate = useNavigate();

  useEffect(() => {
    if (!id) {
      return;
    }
    api.get("/api/listings/" + id)
      .then(({ data }) => {
        setPropertyTitle(data.property_title);
        setLocation(data.location);
        setListingCode(data.listing_code);
        setAvailableUnits(data.available_units);
        setManagerId(String(data.property_manager_id));
        setLoadedId(id);
      })
      .catch((err) => setError(errorMessage(err)));
    fetchManagers().then(setManagers).catch((err) => setError(errorMessage(err)));
  }, [id]);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    try {
      await dispatch(updateListing({ id, listing: {
        property_title: propertyTitle,
        location,
        listing_code: listingCode,
        available_units: Number(availableUnits),
        property_manager_id: Number(managerId),
      } })).unwrap();
      navigate("/");
    } catch (err) {
      setError(typeof err === "string" ? err : err.message);
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
            required
            maxLength={255}
            value={propertyTitle}
            onChange={(event) => setPropertyTitle(event.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="location">Location</label>
          <input
            id="location"
            required
            maxLength={255}
            value={location}
            onChange={(event) => setLocation(event.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="listing-code">Listing Code</label>
          <input id="listing-code" required pattern="RH-0686-[0-9]{5,}" maxLength={50} value={listingCode} onChange={(event) => setListingCode(event.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="available-units">Available Units</label>
          <input id="available-units" type="number" required min="0" step="1" value={availableUnits} onChange={(event) => setAvailableUnits(event.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="manager">Property Manager</label>
          <select id="manager" required value={managerId} onChange={(event) => setManagerId(event.target.value)}>
            <option value="">Select a manager</option>
            {managers.map((manager) => <option key={manager.id} value={manager.id}>{manager.first_name} {manager.last_name}</option>)}
          </select>
        </div>
        <button className="btn primary" type="submit" disabled={loadedId !== id || saving || managers.length === 0}>
          Update Listing
        </button>
      </form>
    </section>
  );
}

export default UpdateRecord;
