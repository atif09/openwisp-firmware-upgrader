"use strict";

django.jQuery(function ($) {
  function initSelect2() {
    if (!$.fn.select2) return;
    $('select[id^="id_firmwareimage_set"][id$="type"]')
      .not('select[name*="__prefix__"]')
      .select2();
  }
  $(".add-row > a").click(initSelect2);
  initSelect2();

  var isBuildChangeForm = $("body").hasClass("model-build") &&
                          $("body").hasClass("change-form");
  if (!isBuildChangeForm) {
    var needsPolling = $(
      ".ow-status-badge.ow-status-info, .ow-status-badge.ow-status-warning, .ow-status-badge.ow-status-grey"
    ).length > 0;
    if (needsPolling) {
      setTimeout(function () {
        location.reload();
      }, 5000);
    }
  }
});
