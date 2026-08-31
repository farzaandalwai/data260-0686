const form = document.getElementById("rentalForm");

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

form.addEventListener("submit", (e) => {
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

    console.log("Updated listing:", updatedData);
    console.log("Submission count:", countSubmit());
});