import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import { createListing } from "../features/listings/listingsSlice";
import { errorMessage, fetchManagers } from "../api/axios";

function CreateRecord() {
  const [propertyTitle, setPropertyTitle] = useState("");
  const [location, setLocation] = useState("");
  const [error, setError] = useState("");
  const [listingCode, setListingCode] = useState("");
  const [availableUnits, setAvailableUnits] = useState(1);
  const [managerId, setManagerId] = useState("");
  const [managers, setManagers] = useState([]);
  const dispatch = useDispatch();
  const saving = useSelector((state) => state.listings.status === "loading");
  const navigate = useNavigate();

  useEffect(() => {
    fetchManagers().then(setManagers).catch((err) => setError(errorMessage(err)));
  }, []);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    try {
      await dispatch(createListing({
        property_title: propertyTitle,
        location,
        listing_code: listingCode,
        available_units: Number(availableUnits),
        property_manager_id: Number(managerId),
      })).unwrap();
      navigate("/");
    } catch (err) {
      setError(typeof err === "string" ? err : err.message);
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
          <input id="listing-code" required pattern="RH-0686-[0-9]{5,}" maxLength={50} placeholder="RH-0686-05001" value={listingCode} onChange={(event) => setListingCode(event.target.value)} />
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
        <button className="btn primary" type="submit" disabled={saving || managers.length === 0}>
          Add Listing
        </button>
      </form>
    </section>
  );
}

export default CreateRecord;
