/* NYX / EOS theme toggle — same behaviour as aiinsocietyhub.com.
   Runs from <head> so the class is set before first paint (no flash). */
(function () {
  if (localStorage.getItem("gaid-theme") === "nyx") {
    document.documentElement.classList.add("nyx");
  }
  addEventListener("DOMContentLoaded", function () {
    /* Typewriter page title — cloned from the site's TypewriterText
       component (speed 40ms, blue caret, caret hidden on completion). */
    var h1 = document.querySelector(".page-title h1");
    if (h1) {
      var full = h1.textContent.trim();
      h1.textContent = "";
      var span = document.createElement("span");
      var caret = document.createElement("span");
      caret.className = "tw-caret";
      h1.appendChild(span);
      h1.appendChild(caret);
      var i = 0;
      var timer = setInterval(function () {
        i++;
        span.textContent = full.slice(0, i);
        if (i >= full.length) {
          clearInterval(timer);
          span.textContent = full;
          caret.style.opacity = "0";
        }
      }, 40);
    }

    var btn = document.getElementById("theme-toggle");
    if (!btn) return;
    function label() {
      // the button names the theme you would switch TO (as on the main site)
      btn.textContent = document.documentElement.classList.contains("nyx")
        ? "Ἠώς" : "Νύξ";
    }
    label();
    btn.addEventListener("click", function () {
      document.documentElement.classList.toggle("nyx");
      localStorage.setItem("gaid-theme",
        document.documentElement.classList.contains("nyx") ? "nyx" : "eos");
      label();
      dispatchEvent(new Event("gaid-theme"));
    });
  });
})();
