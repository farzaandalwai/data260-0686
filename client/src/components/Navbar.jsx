import { Link } from "react-router-dom";

function Navbar({ user, onLogout }) {
  return (
    <nav className="navbar">
      <div className="nav-inner">
        <Link className="brand" to="/">
          Rental Housing Listings
        </Link>
        <div className="nav-links">
          <Link to="/">Home</Link>
          {user ? (
            <>
              <Link to="/create">Add Listing</Link>
              <span className="nav-user">{user.name}</span>
              <button className="btn secondary" type="button" onClick={onLogout}>
                Logout
              </button>
            </>
          ) : (
            <Link to="/login">Login</Link>
          )}
        </div>
      </div>
    </nav>
  );
}

export default Navbar;
