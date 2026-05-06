(function () {
    function danishSlugify(text) {
        return text
            .toLowerCase()
            .replace(/æ/g, 'ae')
            .replace(/ø/g, 'oe')
            .replace(/å/g, 'aa')
            .replace(/[^a-z0-9]+/g, '-')
            .replace(/^-+|-+$/g, '');
    }

    function bindLivePreview(sourceId, targetId) {
        const source = document.getElementById(sourceId);
        const target = document.getElementById(targetId);
        if (!source || !target) return;

        // Kør kun auto-preview hvis brugeren ikke selv har redigeret target
        let brugerHarRedigeret = target.value.trim().length > 0;

        target.addEventListener('input', function () {
            brugerHarRedigeret = true;
        });

        source.addEventListener('input', function () {
            if (!brugerHarRedigeret) {
                target.value = danishSlugify(source.value);
            }
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        // Event-form: titel → slug
        bindLivePreview('id_titel', 'id_slug');
        // Deltager-form: navn → token
        bindLivePreview('id_navn', 'id_token');
    });
})();