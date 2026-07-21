async function refreshJob() {
  const job = document.querySelector("[data-job-id]");
  if (!job) return;
  const id = job.dataset.jobId;
  const response = await fetch(`/api/jobs/${id}`);
  if (!response.ok) return;
  const data = await response.json();
  const progress = job.querySelector("progress");
  const count = job.querySelector(".job-count");
  const status = job.querySelector(".job-status");
  const previousStatus = job.dataset.jobStatus;
  progress.max = data.total || 1;
  progress.value = data.processed || 0;
  count.textContent = `${data.processed}/${data.total}`;
  if (status) status.textContent = data.status;
  job.dataset.jobStatus = data.status;
  if (previousStatus === "running" && data.status !== "running") {
    window.location.reload();
    return;
  }
  if (data.status === "running") {
    window.setTimeout(refreshJob, 2500);
  }
}

refreshJob();
