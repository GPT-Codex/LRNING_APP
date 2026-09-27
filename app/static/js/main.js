// JavaScript utilities for Exam Mistake Tracker

document.addEventListener("DOMContentLoaded", function () {
  // 1. Initialize KaTeX rendering if renderMathInElement is available
  if (window.renderMathInElement) {
    renderMathInElement(document.body, {
      delimiters: [
        { left: "$$", right: "$$", display: true },
        { left: "$", right: "$", display: false },
        { left: "\\(", right: "\\)", display: false },
        { left: "\\[", right: "\\]", display: true }
      ],
      throwOnError: false
    });
  }

  // 2. Mobile Sidebar Toggle
  const mobileToggle = document.getElementById("mobileToggle");
  const sidebar = document.getElementById("sidebar");
  if (mobileToggle && sidebar) {
    mobileToggle.addEventListener("click", function () {
      sidebar.classList.toggle("open");
    });
  }

  // 3. Dynamic Option Addition for MCQ Questions
  const addOptionBtn = document.getElementById("addOptionBtn");
  const optionsContainer = document.getElementById("optionsContainer");
  if (addOptionBtn && optionsContainer) {
    addOptionBtn.addEventListener("click", function () {
      const optionCount = optionsContainer.children.length;
      const labels = ["A", "B", "C", "D", "E", "F", "G", "H"];
      const label = labels[optionCount] || `Opt ${optionCount + 1}`;

      const div = document.createElement("div");
      div.className = "option-card-row";
      div.style.cssText = "background: #ffffff; border: 1px solid var(--border-color); padding: 12px; border-radius: var(--border-radius-sm); margin-bottom: 8px;";
      div.innerHTML = `
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
          <input type="checkbox" name="option_correct_${optionCount}" value="1" title="Mark as correct">
          <span style="font-weight: 700; min-width: 24px;">${label}.</span>
          <input type="text" name="option_text_${optionCount}" class="form-control" placeholder="Option ${label} text (optional if image present)...">
          <button type="button" class="btn btn-secondary btn-sm remove-option-btn" title="Remove Option">&times;</button>
        </div>
        <div style="display: flex; align-items: center; gap: 12px; margin-left: 32px;">
          <label style="font-size: 0.8rem; color: var(--text-secondary);">Option Image:</label>
          <input type="file" name="option_image_${optionCount}" class="form-control" accept="image/*" style="font-size: 0.8rem; padding: 4px;">
        </div>
      `;
      optionsContainer.appendChild(div);

      div.querySelector(".remove-option-btn").addEventListener("click", function () {
        div.remove();
      });
    });
  }

  // 4. Keyboard Navigation in Exam Workspace
  const workspaceForm = document.getElementById("workspaceQuestionForm");
  if (workspaceForm) {
    document.addEventListener("keydown", function (e) {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        const nextBtn = document.getElementById("btnSaveNext");
        if (nextBtn) nextBtn.click();
        else workspaceForm.submit();
      }
    });
  }

  // 5. Active Recall Review Reveal Toggle
  const revealBtn = document.getElementById("revealAnswerBtn");
  const solutionBox = document.getElementById("solutionRevealBox");
  if (revealBtn && solutionBox) {
    revealBtn.addEventListener("click", function () {
      solutionBox.style.display = "block";
      revealBtn.style.display = "none";
      if (window.renderMathInElement) {
        renderMathInElement(solutionBox, {
          delimiters: [
            { left: "$$", right: "$$", display: true },
            { left: "$", right: "$", display: false }
          ],
          throwOnError: false
        });
      }
    });
  }
});

// Dependent Subject -> Chapter selector logic
function setupDependentSubjectChapter(subjectElemId, chapterElemId, subjectsData) {
  const subjectElem = document.getElementById(subjectElemId);
  const chapterElem = document.getElementById(chapterElemId);
  if (!subjectElem || !chapterElem) return;

  function updateChapters() {
    const selectedSubjId = subjectElem.value;
    const currentSelectedChapId = chapterElem.dataset.selectedChapter || chapterElem.value;
    chapterElem.innerHTML = '';

    if (!selectedSubjId) {
      chapterElem.disabled = true;
      const opt = document.createElement('option');
      opt.value = '';
      opt.textContent = '[ Select a subject first ]';
      chapterElem.appendChild(opt);
      return;
    }

    chapterElem.disabled = false;
    const placeholderOpt = document.createElement('option');
    placeholderOpt.value = '';
    placeholderOpt.textContent = '-- Choose Chapter --';
    chapterElem.appendChild(placeholderOpt);

    const subj = subjectsData.find(s => String(s.id) === String(selectedSubjId));
    if (subj && subj.sorted_chapters) {
      subj.sorted_chapters.forEach(ch => {
        const opt = document.createElement('option');
        opt.value = ch.id;
        opt.textContent = ch.name;
        if (String(currentSelectedChapId) === String(ch.id)) {
          opt.selected = true;
        }
        chapterElem.appendChild(opt);
      });
    }
  }

  subjectElem.addEventListener('change', function() {
    chapterElem.dataset.selectedChapter = '';
    updateChapters();
  });

  updateChapters();
}
