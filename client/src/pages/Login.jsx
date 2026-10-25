import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { sendJson } from "../api";

function Login({ setUser }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    try {
      const data = await sendJson("/auth/login", "POST", {
        username,
        password,
      });
      sessionStorage.setItem("hw7_token", data.access_token);
      setUser(data.user);
      navigate("/");
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section className="card login-card">
      <h1>Login</h1>
      <form onSubmit={handleSubmit}>
        {error ? <p className="error">{error}</p> : null}
        <div className="field">
          <label htmlFor="username">Username</label>
          <input
            id="username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </div>
        <button className="btn primary" type="submit">
          Login
        </button>
      </form>
    </section>
  );
}

export default Login;
