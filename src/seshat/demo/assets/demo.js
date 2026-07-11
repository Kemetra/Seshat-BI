document.querySelectorAll("[data-stage-target]").forEach((button) => {
  button.addEventListener("click", () => {
    const target = document.querySelector(`[data-stage="${button.dataset.stageTarget}"]`);
    if (!target) return;
    document.querySelectorAll(".stage-detail").forEach((stage) => stage.classList.remove("is-focused"));
    target.classList.add("is-focused");
    target.scrollIntoView({ behavior: "smooth", block: "start" });
  });
});

