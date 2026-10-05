import { configureStore } from "@reduxjs/toolkit";
import listingsReducer from "../features/listings/listingsSlice.js";

const store = configureStore({
  reducer: { listings: listingsReducer },
});

export default store;
