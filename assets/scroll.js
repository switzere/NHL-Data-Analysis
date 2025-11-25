document.addEventListener("DOMContentLoaded", function () {
    const scrollTarget = document.getElementById("scroll-target");
    const scrollContainer = document.querySelector(".schedule-container");
    const gameCard = document.querySelector(".game-card");

    if (scrollTarget && scrollContainer) {
        // Calculate the position of the target relative to the container
        const targetPosition = scrollTarget.offsetLeft - scrollContainer.offsetLeft;

        // Scroll the container horizontally to the target
        scrollContainer.scrollTo({
            left: targetPosition,
            behavior: "smooth"
        });
    }
});