function () {
    // forceDisableDarkMode
    document.body.classList.remove("dark");
    // update footer
    const footer = document.querySelector("footer");
    footer.innerHTML = `<small style="color: dimgray; margin: 2px;">
        MergeUI is a new project and any <a href="https://github.com/naskio/mergeui" style="color: #f43f5d;" target="_blank">
        contribution 🤗</a> would make a difference!
        </small>`;
}
