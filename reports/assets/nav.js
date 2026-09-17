(function () {
  function setNavState(button, nav, expanded) {
    button.setAttribute("aria-expanded", expanded ? "true" : "false");
    nav.classList.toggle("open", expanded);
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".site-header").forEach(function (header) {
      var button = header.querySelector(".nav-toggle");
      var nav = header.querySelector("nav");
      if (!button || !nav) return;

      setNavState(button, nav, false);

      button.addEventListener("click", function () {
        var expanded = button.getAttribute("aria-expanded") === "true";
        setNavState(button, nav, !expanded);
      });

      nav.querySelectorAll("a").forEach(function (link) {
        link.addEventListener("click", function () {
          setNavState(button, nav, false);
        });
      });

      window.addEventListener("resize", function () {
        if (window.innerWidth > 760) {
          nav.classList.remove("open");
          button.setAttribute("aria-expanded", "false");
        }
      });
    });
  });
})();
