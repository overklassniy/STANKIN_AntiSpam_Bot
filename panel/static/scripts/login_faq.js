document.addEventListener("DOMContentLoaded", function () {
    const faqLink = document.getElementById("faq_link");
    const faqText = document.getElementById("faq_text");
    const commandText = document.getElementById("command")

    if (faqLink && faqText) {
        faqLink.addEventListener("click", function (event) {
            event.preventDefault();
            faqText.classList.toggle("faq-visible");
            commandText.classList.toggle("command-visible")
        });
    }
});
