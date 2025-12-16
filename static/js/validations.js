// Bootstrap validation
(() => {
	"use strict";

	const forms = document.querySelectorAll(".needs-validation");
	Array.from(forms).forEach((form) => {
		form.addEventListener(
			"submit",
			(event) => {
				if (!form.checkValidity()) {
					event.preventDefault();
					event.stopPropagation();
				}
				form.classList.add("was-validated");
			},
			false
		);
	});
})();

// Input format helpers
document.addEventListener("DOMContentLoaded", () => {
  // Phone mask: +998 99 999 99 99
  const phoneInputs = document.querySelectorAll(
    'input[name*="phone"], input[type="tel"]'
  );

  phoneInputs.forEach((input) => {
    if (!input.value) {
      input.value = "+998 ";
    } else if (!input.value.startsWith("+998")) {
      input.value = "+998 " + input.value.replace(/[^0-9]/g, "");
    }

    input.addEventListener("focus", () => {
      if (!input.value || input.value === "+998") {
        input.value = "+998 ";
      }
      const length = input.value.length;
      input.setSelectionRange(length, length);
    });

    input.addEventListener("input", () => {
      let digits = input.value.replace(/\D/g, "");
      if (!digits.startsWith("998")) {
        digits = "998" + digits.replace(/^998/, "");
      }
      digits = digits.substring(0, 12);
      let formatted = "+998";
      const rest = digits.substring(3);
      if (rest.length > 0) {
        formatted += " " + rest.substring(0, 2);
      }
      if (rest.length > 2) {
        formatted += " " + rest.substring(2, 5);
      }
      if (rest.length > 5) {
        formatted += " " + rest.substring(5, 7);
      }
      if (rest.length > 7) {
        formatted += " " + rest.substring(7, 9);
      }
      input.value = formatted;
    });
  });

  // Passport mask: AA1234567
  const passportInputs = document.querySelectorAll(
    'input[name="passport"], input[name="client_passport"], input[name="passport_number"]'
  );

  passportInputs.forEach((input) => {
    input.addEventListener("input", () => {
      let value = input.value.toUpperCase().replace(/[^A-Z0-9]/g, "");
      let letters = value.replace(/[^A-Z]/g, "").substring(0, 2);
      let numbers = value.replace(/[^0-9]/g, "").substring(0, 7);
      input.value = letters + numbers;
    });
  });

  // Date mask: DD.MM.YYYY for text inputs (not type="date")
  const dateInputs = document.querySelectorAll(
    'input[name="muddat"], input[name="passport_issue_date"], input[name="passport_expiry_date"], input[name="birth_date"], input[data-date-mask="true"]'
  );

  dateInputs.forEach((input) => {
    input.addEventListener("input", () => {
      let digits = input.value.replace(/\D/g, "").substring(0, 8);
      let result = "";
      if (digits.length > 0) {
        result += digits.substring(0, 2);
      }
      if (digits.length > 2) {
        result += "." + digits.substring(2, 4);
      }
      if (digits.length > 4) {
        result += "." + digits.substring(4, 8);
      }
      input.value = result;
    });
  });
});
