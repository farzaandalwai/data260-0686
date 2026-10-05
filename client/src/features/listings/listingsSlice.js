import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import api, { errorMessage } from "../../api/axios.js";

export const fetchListings = createAsyncThunk("listings/fetch", async (page, { rejectWithValue, getState }) => {
  try {
    const currentPage = page ?? getState().listings.page;
    const response = await api.get("/api/listings", { params: { page: currentPage, page_size: 20 } });
    return response.data;
  } catch (error) {
    return rejectWithValue(errorMessage(error));
  }
});

export const createListing = createAsyncThunk("listings/create", async (listing, { rejectWithValue }) => {
  try {
    return (await api.post("/api/listings", listing)).data;
  } catch (error) {
    return rejectWithValue(errorMessage(error));
  }
});

export const updateListing = createAsyncThunk("listings/update", async ({ id, listing }, { rejectWithValue }) => {
  try {
    return (await api.put("/api/listings/" + id, listing)).data;
  } catch (error) {
    return rejectWithValue(errorMessage(error));
  }
});

export const deleteListing = createAsyncThunk("listings/delete", async (id, { rejectWithValue }) => {
  try {
    await api.delete("/api/listings/" + id);
    return id;
  } catch (error) {
    return rejectWithValue(errorMessage(error));
  }
});

const initialState = { items: [], total: 0, page: 1, page_size: 20, status: "idle", error: "" };

const listingsSlice = createSlice({
  name: "listings",
  initialState,
  reducers: {
    clearListings: () => initialState,
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchListings.fulfilled, (state, action) => {
        Object.assign(state, action.payload);
      })
      .addCase(createListing.fulfilled, (state, action) => {
        state.items.push(action.payload);
        state.total += 1;
        state.page = Math.ceil(state.total / state.page_size);
      })
      .addCase(updateListing.fulfilled, (state, action) => {
        state.items = state.items.map((item) => item.id === action.payload.id ? action.payload : item);
      })
      .addCase(deleteListing.fulfilled, (state, action) => {
        state.items = state.items.filter((item) => item.id !== action.payload);
        state.total -= 1;
      })
      .addMatcher((action) => action.type.startsWith("listings/") && action.type.endsWith("/pending"), (state) => {
        state.status = "loading";
        state.error = "";
      })
      .addMatcher((action) => action.type.startsWith("listings/") && action.type.endsWith("/fulfilled"), (state) => {
        state.status = "succeeded";
      })
      .addMatcher((action) => action.type.startsWith("listings/") && action.type.endsWith("/rejected"), (state, action) => {
        state.status = "failed";
        state.error = action.payload || action.error.message;
      });
  },
});

export const { clearListings } = listingsSlice.actions;
export default listingsSlice.reducer;
