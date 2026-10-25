import axios from "axios";

const api = axios.create({
  baseURL: "http://127.0.0.1:8686",
});

api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem("hw7_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export function errorMessage(error) {
  const detail = error.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((item) => item.msg).join("; ");
  return error.message || "Request failed";
}

export async function fetchManagers() {
  const managers = [];
  let page = 1;
  let total;
  do {
    const response = await api.get("/api/property-managers", { params: { page, page_size: 100 } });
    managers.push(...response.data.items);
    total = response.data.total;
    page += 1;
    if (response.data.items.length === 0) break;
  } while (managers.length < total);
  return managers;
}

export default api;
