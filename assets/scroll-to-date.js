document.addEventListener('DOMContentLoaded', function () {
    const WRAPPER_ID = 'schedule-scroll-wrapper';

    function centerDate(wrapper, dateEl) {
        const left = dateEl.offsetLeft;
        const centerOffset = Math.max(0, Math.round(left - (wrapper.clientWidth - dateEl.offsetWidth) / 2));
        wrapper.scrollLeft = centerOffset;
    }

    function tryFindAndObserve(wrapper) {
        const today = wrapper.dataset.today || new Date().toISOString().slice(0, 10);
        const inner = wrapper.querySelector('.horizontal-scroll__inner');
        const dateEl = inner && (inner.querySelector(`[data-date="${today}"]`) || inner.querySelector(`[data-date^="${today}"]`));
        if (dateEl) {
            centerDate(wrapper, dateEl);
            return;
        }

        // watch for children (rendered later by Dash)
        const targetNode = inner || wrapper;
        const observer = new MutationObserver((mutations, obs) => {
            const innerNow = wrapper.querySelector('.horizontal-scroll__inner');
            const found = innerNow && (innerNow.querySelector(`[data-date="${today}"]`) || innerNow.querySelector(`[data-date^="${today}"]`));
            if (found) {
                centerDate(wrapper, found);
                obs.disconnect();
            }
        });
        observer.observe(targetNode, { childList: true, subtree: true });
    }

    const wrapper = document.getElementById(WRAPPER_ID);
    if (wrapper) {
        tryFindAndObserve(wrapper);
        return;
    }

    // wrapper not present yet — observe the body until it's added, then observe inside it
    const bodyObserver = new MutationObserver((mutations, obs) => {
        const w = document.getElementById(WRAPPER_ID);
        if (w) {
            obs.disconnect();
            tryFindAndObserve(w);
        }
    });
    bodyObserver.observe(document.body, { childList: true, subtree: true });
});