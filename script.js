const form = document.getElementById("rentalForm");
const listingsStatus = document.getElementById("listingsStatus");
const listingsList = document.getElementById("listingsList");
const searchInput = document.getElementById("searchInput");
const searchButton = document.getElementById("searchButton");
const clearSearchButton = document.getElementById("clearSearchButton");

let currentSearch = "";

const makeCounter = () => {
    let count = 0;

    return () => {
        count++;
        return count;
    };
};

const countSubmit = makeCounter();

const validateForm = () => {
    const details = document.getElementById("description").value.trim();
    const terms = document.getElementById("termsAccepted").checked;

    if (details.length <= 25) {
        alert("The property description must be more than 25 characters.");
        return false;
    }

    if (!terms) {
        alert("Please agree to the terms and conditions.");
        return false;
    }

    return true;
};

const showLoading = () => {
    listingsList.innerHTML = "";
    listingsStatus.hidden = false;
    listingsStatus.classList.remove("error");
    listingsStatus.textContent = "Loading listings...";
};

const showEmpty = () => {
    listingsList.innerHTML = "";
    listingsStatus.hidden = false;
    listingsStatus.classList.remove("error");
    listingsStatus.textContent = "No listings found.";
};

const showError = (message = "Unable to load listings.") => {
    listingsList.innerHTML = "";
    listingsStatus.hidden = false;
    listingsStatus.classList.add("error");
    listingsStatus.textContent = message;
};

const renderListings = (listings) => {
    if (!Array.isArray(listings) || listings.length === 0) {
        showEmpty();
        return;
    }

    listingsList.innerHTML = "";
    listingsStatus.hidden = true;
    listingsStatus.classList.remove("error");

    listings.forEach((listing) => {
        const card = document.createElement("article");
        card.className = "listing-card";

        const title = document.createElement("h3");
        title.textContent =
            `#${listing.id} ${listing.propertyTitle || "Untitled Listing"}`;

        const details = document.createElement("p");
        details.className = "listing-meta";
        details.textContent =
            `${listing.location || "Location not provided"} · ` +
            `${listing.propertyType || "Property type not provided"}`;

        const description = document.createElement("p");
        description.textContent =
            listing.description || "No property details provided.";

        const email = document.createElement("p");
        email.textContent =
            `Contact: ${listing.submitterEmail || "Not provided"}`;

        card.append(title, details, description, email);

        if (listing.submissionDate) {
            const date = document.createElement("p");
            date.textContent = `Submitted: ${listing.submissionDate}`;
            card.appendChild(date);
        }

        const actions = document.createElement("div");
        actions.className = "card-actions";

        const editButton = document.createElement("button");
        editButton.type = "button";
        editButton.textContent = "Edit";
        editButton.addEventListener("click", () => updateListing(listing));

        const deleteButton = document.createElement("button");
        deleteButton.type = "button";
        deleteButton.className = "delete-button";
        deleteButton.textContent = "Delete";
        deleteButton.addEventListener(
            "click",
            () => deleteListing(listing.id)
        );

        actions.append(editButton, deleteButton);
        card.appendChild(actions);
        listingsList.appendChild(card);
    });
};

const loadListings = async (search = "") => {
    currentSearch = search;
    showLoading();

    try {
        const query = search ? `?search=${encodeURIComponent(search)}` : "";
        const response = await fetch(`/listings${query}`);

        if (!response.ok) {
            throw new Error("Unable to load listings.");
        }

        const listings = await response.json();
        renderListings(listings);
    } catch (error) {
        showError("Unable to load listings.");
    }
};

const updateListing = async (listing) => {
    const propertyTitle = window.prompt(
        "Property name:",
        listing.propertyTitle
    );

    if (propertyTitle === null) {
        return;
    }

    const location = window.prompt("Location:", listing.location);

    if (location === null) {
        return;
    }

    const { id, ...data } = listing;
    data.propertyTitle = propertyTitle.trim() || listing.propertyTitle;
    data.location = location.trim() || listing.location;

    try {
        const response = await fetch(`/listings/${id}`, {
            method: "PUT",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            throw new Error("Unable to update listing.");
        }

        await loadListings(currentSearch);
    } catch (error) {
        showError("Unable to update listing.");
    }
};

const deleteListing = async (id) => {
    if (!window.confirm("Delete this listing?")) {
        return;
    }

    try {
        const response = await fetch(`/listings/${id}`, {
            method: "DELETE"
        });

        if (!response.ok) {
            throw new Error("Unable to delete listing.");
        }

        await loadListings(currentSearch);
    } catch (error) {
        showError("Unable to delete listing.");
    }
};

const searchListings = () => {
    loadListings(searchInput.value.trim());
};

form.addEventListener("submit", async (e) => {
    e.preventDefault();

    if (!validateForm()) {
        return;
    }

    const data = {
        propertyTitle: document.getElementById("propertyTitle").value.trim(),
        location: document.getElementById("location").value.trim(),
        submitterEmail: document.getElementById("submitterEmail").value.trim(),
        description: document.getElementById("description").value.trim(),
        propertyType: document.getElementById("propertyType").value,
        termsAccepted: document.getElementById("termsAccepted").checked
    };

    const jsonData = JSON.stringify(data, null, 2);
    console.log(jsonData);

    const parsedData = JSON.parse(jsonData);
    const { propertyTitle, submitterEmail } = parsedData;

    console.log("Property title:", propertyTitle);
    console.log("Email:", submitterEmail);

    const updatedData = {
        ...parsedData,
        submissionDate: new Date().toISOString()
    };

    showLoading();

    try {
        const response = await fetch("/listings", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(updatedData)
        });

        if (!response.ok) {
            throw new Error("Unable to create listing.");
        }

        const createdListing = await response.json();
        console.log("Updated listing:", createdListing);
        console.log("Submission count:", countSubmit());

        form.reset();
        searchInput.value = "";
        await loadListings();
    } catch (error) {
        showError("Unable to create listing.");
    }
});

searchButton.addEventListener("click", searchListings);

clearSearchButton.addEventListener("click", () => {
    searchInput.value = "";
    loadListings();
});

searchInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
        searchListings();
    }
});

loadListings();