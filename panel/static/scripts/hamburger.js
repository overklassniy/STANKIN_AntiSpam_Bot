document.addEventListener("DOMContentLoaded", () => {
    const hamburger = document.querySelector(".hamburger");
    const dropdownMenu = document.querySelector(".dropdown-menu");

    hamburger.addEventListener("click", () => {
        dropdownMenu.classList.toggle("show"); // Переключение видимости меню
    });

    // Закрытие меню при клике вне его
    document.addEventListener("click", (event) => {
        if (!hamburger.contains(event.target) && !dropdownMenu.contains(event.target)) {
            dropdownMenu.classList.remove("show");
        }
    });
});
