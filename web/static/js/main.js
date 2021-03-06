
$.fn.removeClassPrefix = function(prefix) {
    this.each(function(i, el) {
	var classes = el.className.split(" ").filter(function(c) {
	    return c.lastIndexOf(prefix, 0) !== 0;
	});
	el.className = $.trim(classes.join(" "));
    });
    return this;
};

function getInterfaceColor() {
    return $('body').attr('class').replace('interface-', '');
}

$('a.page-scroll').bind('click', function(event) {
    var $anchor = $(this);
    $('html, body').stop().animate({
	scrollTop: $($anchor.attr('href')).offset().top
    }, 1500, 'easeInOutExpo');
    event.preventDefault();
});

$("#togglebutton").click(function(e) {
    e.preventDefault();
    $("#wrapper").toggleClass("toggled");
});

function freeModal(title, body, buttons) {
    $('#freeModal .modal-header h4').html(title);
    $('#freeModal .modal-body').html(body);
    $('#freeModal .modal-footer').html('<button type="button" class="btn btn-Smile" data-dismiss="modal">Go</button>');
    if (buttons === 0) {
	$('#freeModal .modal-footer').hide();
    } else if (typeof buttons != 'undefined') {
	$('#freeModal .modal-footer').html(buttons);
	$('#freeModal .modal-footer').show();
    }
    $('#freeModal').modal('show');
}

function globalModal(hash, modal_size) {
    if (hash == 'donate') {
	window.location.href = "/donate/";
	return;
    }
    if (hash == 'about') {
	window.location.href = "/about/";
	return;
    }
    if (typeof modal_size == 'undefined') {
	if (hash == 'tutorialaddcard'
	    || hash == 'aboutllsif'
	    || hash == 'aboutsukutomo'
	   ) {
	    modal_size = 'lg'
	}
    }
    $.get('/ajax/modal/' + hash +
	  '/?interfaceColor=' + getInterfaceColor(), function(data) {
	      $('#modal .modal-content').html(data);
	      $('#modal .modal-dialog').removeClass('modal-lg');
	      $('#modal .modal-dialog').removeClass('modal-sm');
	      if (typeof modal_size != 'undefined') {
		  $('#modal .modal-dialog').addClass('modal-' + modal_size);
	      }
	      $('#modal').modal('show');
	      modalHandler();
	  });
}

function updateActivities() {
    $('[href="#imgur"]').off('click');
    $('[href="#imgur"]').click(function(e) {
	e.preventDefault();
	freeModal('<br>', '<img src="http://i.imgur.com/' + $(this).data('imgur') + '.png" class="img-responsive">');
	return false;
    });
    $('.activity .message.need-to-autolink').each(function() {
	$(this).html(Autolinker.link($(this).html(), { newWindow: true, stripPrefix: true } ));
	$(this).removeClass('need-to-autolink');
    });
    $('.likeactivity').off('submit');
    $('.likeactivity').submit(function(e) {
	e.preventDefault();
	$(this).ajaxSubmit({
	    context: this,
	    success: function(data) {
		if (data == 'liked') {
		    $(this).find('input[type=hidden]').prop('name', 'unlike');
		} else {
		    $(this).find('input[type=hidden]').prop('name', 'like');
		}
		var value = $(this).find('button[type=submit]').html();
		$(this).find('button[type=submit]').html($(this).find('button[type=submit]').attr('data-reverse'));
		$(this).find('button[type=submit]').attr('data-reverse', value);
	    },
	    error: function() {
		alert('Oops! Something bad happened. Try again.');
	    }
	});
    });
    $.each(['markhot', 'removehot', 'bump', 'drown'], function(_, btn) {
	$('a[href="#' + btn + '"]').unbind('click');
	$('a[href="#' + btn + '"]').click(function(e) {
	    e.preventDefault();
	    var button = $(this);
	    $.ajax({
		type: 'POST',
		url: '/ajax/' + btn + '/',
		data: {
		    'activity': button.closest('form').data('activity-id'),
		},
		success: function(data) {
		    button.text('OK');
		},
		error: genericAjaxError,
	    });
	    return false;
	});
    });
}

function genericAjaxError() {
    alert('Oops! Something bad happened. Try again.');
}

function avatarStatus() {
    $('.avatar_wrapper').each(function() {
	if (typeof $(this).attr('data-user-status') != 'undefined') {
	    $(this).popover({
		title: '<span style="color: ' + $(this).css('color') + '">' + $(this).attr('data-user-status') + '</span>',
		content: '<small style="color: #333">School Idol Tomodachi Donator</small>',
		html: true,
		placement: 'bottom',
		trigger: 'hover',
	    });
	}
    });
}

function modalHandler() {
    $('[data-toggle=ajaxmodal]').unbind('click');
    $('[data-toggle=ajaxmodal]').click(function(e) {
	e.preventDefault();
	globalModal($(this).attr('href').replace('#', '').replace('Modal', ''), $(this).data('modal-size'));
    });
}

function formloaders() {
    $('button[data-form-loader=true]').click(function(e) {
	$(this).html('<i class="flaticon-loading"></i>');
	$(this).unbind('click');
	$(this).click(function(e) {
	    e.preventDefault();
	    return false;
	});
    });
}

var alert_displayed = false;

function loadiTunesData(song, successCallback, errorCallback) {
    var itunes_id = song.find('[href="#play"]').data('itunes-id');
    var errorCallback = typeof errorCallback == 'undefined' ? function() {} : errorCallback;
    $.ajax({
	"url": 'https://itunes.apple.com/lookup',
	"dataType": "jsonp",
	"data": {
	    "id": itunes_id,
	    "country": "JP",
	},
	"error": function (jqXHR, textStatus, message) {
	    errorCallback();
	    if (alert_displayed == false) {
		alert('Oops! The song previews don\'t seem to be work anymore. Please contact us and we will fix this.');
		alert_displayed = true;
	    }
	},
	"success": function (data, textStatus, jqXHR) {
	    if (data['results'].length == 0) {
		errorCallback();
		alert('Oops! This song preview (' + song.find('.song_name').text() + ') doesn\'t seem to be valid anymore. Please contact us and we will fix this.');
	    } else {
		successCallback(data);
	    }
	}
    });
}

function loadNotifications(callbackOnLoaded) {
    var usernamebutton = $('[href="#navbarusername"]');
    $.get('/ajax/notifications/', function(data) {
	usernamebutton.popover({
	    container: $('nav.navbar ul.navbar-right'),
	    html: true,
	    placement: 'bottom',
	    content: data,
	    trigger: 'manual',
	});
	usernamebutton.on('shown.bs.popover', function () {
	    $('a[href="#loadmorenotifications"]').unbind('click');
	    $('a[href="#loadmorenotifications"]').click(function(e) {
		e.preventDefault();
		usernamebutton.popover('destroy');
		loadNotifications();
		return false;
	    });
	});
	usernamebutton.popover('show');
	if (typeof callbackOnLoaded != 'undefined') {
	    callbackOnLoaded();
	}
    });
}

function notificationsHandler() {
    var usernamebutton = $('[href="#navbarusername"]');
    $('[href="#notifications"]').click(function(e) {
	e.preventDefault();
	var button = $(this);
	button.html('<i class="flaticon-loading"></i>');
	loadNotifications(function() {
	    button.closest('li').remove();
	});
	return false;
    });
    $('body').on('click', function (e) {
	if ($(e.target).data('toggle') !== 'popover'
	    && $(e.target).parents('.popover.in').length === 0) {
	    usernamebutton.popover('hide');
	}
    });
}

$(document).ready(function() {
    var hash = window.location.hash.substring(1);
    if (hash.indexOf("Modal") >= 0) {
	globalModal(hash.replace('Modal', ''));
    }

    modalHandler();

    if ($('#notifications').length > 0) {
	$('#notifications').popover('show');
	// dismiss on click on navbar
	$('nav').on('click', function (e) {
	    if ($(e.target).data('toggle') !== 'popover'
		&& $(e.target).parents('.popover.in').length === 0) {
		$('#notifications').popover('hide');
	    }
	});
    }

    $('.switchLanguage').click(function(e) {
	e.preventDefault();
	$('#switchLanguage').find('select').val($(this).attr('data-lang'));
	$('#switchLanguage').submit();
    });

    updateActivities();
    avatarStatus();

    notificationsHandler();

    formloaders();
});

(function () {
    var s = document.createElement('script'); s.async = true;
    s.type = 'text/javascript';
      s.src = '//' + disqus_shortname + '.disqus.com/count.js';
    (document.getElementsByTagName('HEAD')[0] || document.getElementsByTagName('BODY')[0]).appendChild(s);
}());
