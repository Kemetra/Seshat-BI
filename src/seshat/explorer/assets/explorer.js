document.querySelectorAll("[data-table-target]").forEach((button) => {
  button.addEventListener("click", () => {
    const target = document.querySelector(`[data-table="${button.dataset.tableTarget}"]`);
    if (!target) return;
    document.querySelectorAll(".table-card").forEach((card) => card.classList.remove("is-focused"));
    target.classList.add("is-focused");
    target.scrollIntoView({ behavior: "smooth", block: "start" });
  });
});

document.querySelectorAll("[data-stage-target]").forEach((button) => {
  button.addEventListener("click", () => {
    const target = document.querySelector(`[data-stage="${button.dataset.stageTarget}"]`);
    if (!target) return;
    document.querySelectorAll(".stage-detail").forEach((stage) => stage.classList.remove("is-focused"));
    target.classList.add("is-focused");
    target.scrollIntoView({ behavior: "smooth", block: "start" });
  });
});
