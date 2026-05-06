(function($) {
    $(document).ready(function() {
        const navnFelt = $('#id_navn');
        const tokenFelt = $('#id_token');

        navnFelt.on('input', function() {
            const slug = $(this).val()
                .toLowerCase()
                .replace(/æ/g, 'ae')
                .replace(/ø/g, 'oe')
                .replace(/å/g, 'aa')
                .replace(/[^a-z0-9]+/g, '-')
                .replace(/^-+|-+$/g, '');
            tokenFelt.val(slug);
        });
    });
})(django.jQuery || jQuery);
