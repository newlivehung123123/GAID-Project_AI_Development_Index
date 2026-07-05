/* NYX / EOS theme toggle — same behaviour as aiinsocietyhub.com.
   Runs from <head> so the class is set before first paint (no flash). */
(function () {
  if (localStorage.getItem("gaid-theme") === "nyx") {
    document.documentElement.classList.add("nyx");
  }
  addEventListener("DOMContentLoaded", function () {
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
