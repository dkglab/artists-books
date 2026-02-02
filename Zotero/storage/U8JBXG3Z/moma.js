
// Patch for MooTools 1.2.5 compatibility with Firefox 18
String.prototype.contains = function(string, separator) {
  return (separator) ? (separator + this + separator).indexOf(separator + string + separator) > -1 : String(this).indexOf(string) > -1;
};

/*

Class: Controllers

This is a namespace for all the classes that control interactive behavior on the
page. It also manages event messaging so that controllers can communicate with
each other.

*/
var Controllers = new Class({

  Implements: Events,

  initialize: function(cssPrefix) {
    this.cssPrefix = cssPrefix;
    this.controllers = [];
    this.countdown = 2;
    window.addEvent('domready', this.onReady.bind(this));
    this.addEvent('onReady', this.onReady.bind(this));
  },

  onReady: function() {

    // In order to initialize controllers safely, wait to make sure that both
    // the DOM is ready and that the 'onReady' custom event has been fired.
    // Firing 'onReady' indicates that all controllers have been added.
    this.countdown--;
    if (this.countdown === 0) {
      this.fireEvent('onBeforeInitialize');
      this.initializeControllers();
      this.fireEvent('onAfterInitialize');
    }
  },

  initializeControllers: function(target) {

    var matches, selector;

    // After the page loads, search for elements with particular CSS classes
    // that correspond to JavaScript behavior controllers. Or if target is
    // included as an argument, initialize controllers within its contents.

    // Some special cases
    $$('img[longdesc]').addClass('JS_ImageCaption');
    $$('a.ss-send-to-phone').addClass('JS_SendToPhone');

    for (var property in this) {
      if ($type(this[property]) == 'class') {
        selector = '.' + this.cssPrefix + property;
        if ($type(target) == 'element') {
          matches = target.getElements(selector);
        } else {
          matches = $$(selector);
        }
        var el;
        for (var i = 0; i < matches.length; i++) {
          el = matches[i];
          try {
            var controllerClass = this[property];
            var controllerObject = new controllerClass(el, this);
            this.controllers.push(controllerObject);
          } catch(e) {
            this.handleException(e);
          }
        }
      }
    }

    if ($type(target) == 'element') {
      this.fireEvent('onWidgetInitialize', target);
    } else {

      // Notify any listeners that all controllers are done initializing. Also,
      // set a top-level CSS class to allow for progressive enhancement.

      this.fireEvent('onInitialize');
      $(document.body).addClass(this.cssPrefix + 'enabled');
    }

  },

  handleException: function(e) {
    dbug.log("Error: " + e.message +
             " [" + this.getExceptionOrigin(e) + "] ");
  },

  getExceptionOrigin: function(e) {
    if (e.fileName) {
      var file = e.fileName.match(/\/([^\/?]+)[^\/]*$/)[1];
      return file + ':' + e.lineNumber;
    } else {
      return "unknown origin";
    }
  }

});

var MoMA = new Controllers('JS_');

MoMA.Calendar = new Class({

  initialize: function(el, page) {
    this.el = el;
    this.page = page;
    this.el.getElements('.tabs a').each(function(tab) {
      tab.addEvent('click', this.tabClick.bind(this));
    }.bind(this));
  },

  tabClick: function(e) {
    e = new Event(e);
    e.preventDefault();

    this.el.getElement('.events .selected').removeClass('selected');
    this.el.getElement('.tabs .selected').removeClass('selected');

    var target = $(e.target).getAttribute('href').match(/#(.+)/)[1];
    $('tab-' + target).addClass('selected');
    $(e.target).addClass('selected');

    var date = this.el.getElement('.date');
    if (date) {
      date.set('html', $(e.target).get('rel'));
    }
  }

});

MoMA.Promotions = new Class({

  initialize: function(el, page) {

    var items = el.getElements('.item');

    if (items.length < 5) {
      el.getElement('.next').addClass('disabled');
    }

    if (items.length === 0) {
      return;
    }

    this.el = el;
    this.offset = 0;
    this.pageSize = items[0].getSize().x +
                    parseInt(items[0].getStyle('margin-right'), 10) +
                    parseInt(items[0].getStyle('margin-left'), 10);

    var contentWidth = el.getElement('.content').getSize().x;
    this.max = items.length * this.pageSize - contentWidth - 10;



    el.getElement('.prev').addEvent('click', this.prev.bind(this));
    el.getElement('.next').addEvent('click', this.next.bind(this));
    el.getElement('.slider').set('tween', {
      duration: 750,
      transition: Fx.Transitions.Quart.easeOut
    });
  },

  next: function() {

    if (this.el.getElement('.next').hasClass('disabled')) {
      return false;
    }
    this.offset -= this.pageSize;
    this.el.getElement('.slider').tween('left', this.offset);
    if (this.offset < -this.max) {
      this.el.getElement('.next').addClass('disabled');
    }
    this.el.getElement('.prev').removeClass('disabled');
    return false;
  },

  prev: function() {
    if (this.el.getElement('.prev').hasClass('disabled')) {
      return false;
    }
    this.offset += this.pageSize;
    this.el.getElement('.slider').tween('left', this.offset);
    if (this.offset === 0) {
      this.el.getElement('.prev').addClass('disabled');
    }
    this.el.getElement('.next').removeClass('disabled');
    return false;
  }

});

MoMA.HeroImages = new Class({

  Implements: [Options, Events],

  options: {
    distanceFromPageBottom: 95,
    maxHeight: 1000,
    minHeight: 530,
    sliderWaitDuration: 6500,
    sliderFx: { // Sliding items vertically
      duration: 1500,
      transition: Fx.Transitions.Quart.easeOut
    },
    infoFx: { // Shifting the info text vertically on hover
      duration: 500,
      transition: Fx.Transitions.Quart.easeOut
    },
    contentFx: { // Fading content text in and out
      duration: 375,
      transition: Fx.Transitions.Quart.easeOut
    },
    thumbsFx: { // Sliding the thumbnails horizontally
      duration: 500,
      transition: Fx.Transitions.Quart.easeOut
    },
    arrowsFx: { // Nav arrows sliding in vertically
      duration: 250,
      transition: Fx.Transitions.Quart.easeOut
    }
  },

  initialize: function(el, page) {
    this.el = el;
    this.page = page;
    this.hover = false;
    this.index = 0;
    this.count = 0;
    this.video = null;
    this.imageQueue = [];
    this.imageLoaded = {};
    this.timeMadeVisible = null;
    if (!Browser.Engine.trident) {
      window.addEvent('load', this.setup.bind(this));
    } else {
      this.setup();
    }
    window.addEvent('resize', this.resize.bind(this));
  },

  setup: function() {
    this.setupItems();
    this.setupSlider();
    this.resize();
    this.setupThumbs();
    this.setupBookends();
    this.loadImages();
    this.setupInfo();
    this.setupArrows();
    this.setupEvents();
    this.page.heroImagesAreSetup = true;
    this.page.fireEvent('heroImagesSetup');
  },

  setupItems: function() {
    this.el.getElements('.slider .item').each(function(item) {

      // Discard items that are scheduled to show, but not right now
      if (!item.timeCheck()) {
        item.destroy();
        return;
      }

      // Only allow 6 items total
      if (this.count == 6) {
        item.destroy();
        return;
      }

      var info = item.getElement('.info');
      info.set('tween', this.options.infoFx);
      var content = this.getContent(info);
      content.set('tween', this.options.contentFx);

      var image = item.getElement('.image');
      image.store('item-number', this.count);
      image.addClass('item' + this.count);
      this.imageQueue.push(image);
      this.imageLoaded[this.count] = false;

      var collapsedHeight = info.getSize().y;
      info.store('collapsed-height', collapsedHeight);
      info.inject(this.el);
      info.addClass('setup');

      if (this.count == 0) {
        info.addClass('current-info');
      } else {
        content.fade('hide');
      }

      var titleLink = info.getElement('h2 a');
      var title = titleLink.get('html');
      if (item.get('data-thumbnail-title') && item.get('data-thumbnail-title') != '') {
        title = item.get('data-thumbnail-title');
      }
      item.store('thumbnail-title', title);
      item.store('image-url', item.getElement('.image-link').get('href'));

      this.addEvent('resize', function() {
        info.setStyles({
          top: this.itemHeight - collapsedHeight,
          bottom: 'auto'
        });
      }.bind(this));

      if (item.get('data-video-src')) {
        this.setupItemVideo(item);
      }
      if (isTouchUI()) {
        this.setupItemTouchEvents(item);
      }

      this.count++;
    }.bind(this));
  },

  setupSlider: function() {
    var slider = this.el.getElement('.slider');
    slider.setStyle('top', 0);
    var fxOptions = this.options.sliderFx;
    fxOptions.onStart = function() {
      this.sliderTween.isRunning = true;
    }.bind(this);
    fxOptions.onComplete = function() {
      this.sliderTween.isRunning = false;
      this.index = this.index % this.count;
      this.el.getElement('.slider').setStyle('top', this.index * -this.itemHeight);
    }.bind(this);
    this.sliderTween = new Fx.Tween(slider, fxOptions);
    this.addEvent('resize', function() {
      var height = this.el.getSize().y;
      slider.setStyle('top', this.index * -height);
      var bookendBefore = this.el.getElement('.bookend-before');
      if (bookendBefore) {
        bookendBefore.setStyle('margin-top', height * -this.count);
      }
    }.bind(this));
  },

  resize: function() {
    if (this.sliderTween && this.sliderTween.isRunning) {
      if (this.resizeTimeout) {
        clearTimeout(this.resizeTimeout);
      }
      this.resizeTimeout = setTimeout(this.resize.bind(this), 100);
    } else {
      this.stopInterval();
      if (!this.video && !this.el.hasClass('hidden-before-onload')) {
        this.startInterval();
      }
      var itemHeight = window.getSize().y - this.el.getPosition().y - this.options.distanceFromPageBottom;
      itemHeight = Math.min(this.options.maxHeight, itemHeight);
      itemHeight = Math.max(this.options.minHeight, itemHeight);
      this.itemHeight = itemHeight;
      this.el.setStyle('height', this.itemHeight);
      this.el.getElements('.item').each(function(item) {
        item.setStyle('height', this.itemHeight);
      }.bind(this));
      this.fireEvent('resize');
    }
  },

  setupThumbs: function() {
    var thumbs = this.el.getElement('.thumbs');
    var slider = this.el.getElement('.slider');
    thumbs.set('tween', this.options.thumbsFx);
    slider.getElements('.item').each(function(item, index) {
      var titleText = item.retrieve('thumbnail-title');
      var titleSpan = isTouchUI() ? '' : '<span class="title">' + titleText + '</span>';
      var link = new Element('a', {
        'class': 'item' + index,
        href: item.retrieve('image-url'),
        html: '<span class="fade"></span>' +
              titleSpan
      }).inject(thumbs);
      if (!isTouchUI()) {
        var title = link.getElement('.title');
        var titleHeight = title.getSize().y;
        title.store('height', titleHeight);
        title.setStyle('top', Math.round((75 - titleHeight) / 2));
        title.addClass('setup');
      }
      if (item.get('data-is-store-item') == 'true') {
        var storeBanner = new Element('span', {
          'class': 'store-item',
          html: 'MoMA <span>STORE</span>'
        }).inject(link);
      }
      link.addEvent('click', function(e) {
        new Event(e).stop();
        if (!isTouchUI() && this.index != index && this.isImageLoaded(index)) {
          this.index = index;
          this.rotate();
        }
      }.bind(this));
      if (isTouchUI()) {
        link.addEvent('touchstart', function(e) {
          if (this.index != index && this.isImageLoaded(index)) {
            this.index = index;
            this.rotate();
          }
        }.bind(this));
      } else {
        link.addEvent('mouseenter', function() {
          if (!link.hasClass('current-thumb')) {
            link.getElement('.fade').fade('show');
          } else {
            link.getElement('.title').fade('show');
          }
        });
        link.addEvent('mouseleave', function() {
          if (!link.hasClass('current-thumb')) {
            link.getElement('.fade').fade('hide');
          } else {
            link.getElement('.title').fade('hide');
          }
        });
      }
      if (index == 0) {
        link.addClass('current-thumb');
        if (link.getElement('.title')) {
          link.getElement('.title').fade('hide');
        }
      } else {
        link.getElement('.fade').fade('hide');
      }
      var videoSrc = item.get('data-video-src');
      if (videoSrc && videoSrc != '') {
        var play = new Element('div', {
          'class': 'video-play'
        }).inject(link);
      }
    }.bind(this));
    var resizeThumbs = function() {
      var thumbLinks = thumbs.getElements('a');
      var numThumbs = thumbLinks.length;
      var thumbHeight = Math.round((this.itemHeight - 30) / numThumbs);
      thumbHeight = Math.max(thumbHeight, 85);
      thumbHeight = Math.min(thumbHeight, 138);
      thumbLinks.each(function(thumb) {
        var height = thumbHeight - 10;
        thumb.setStyle('height', height);
        var title = thumb.getElement('.title');
        if (title) {
          var top = Math.round((height - title.retrieve('height')) / 2);
          top = Math.max(0, top);
          title.setStyle('top', top);
        }
      });
      var totalHeight = thumbHeight * numThumbs - 10;
      var thumbsMargin = Math.round((this.itemHeight - totalHeight) / 2) - 15;
      thumbsMargin = Math.max(0, thumbsMargin);
      thumbLinks[0].setStyle('margin-top', thumbsMargin);
    }.bind(this);
    resizeThumbs();
    this.addEvent('resize', resizeThumbs);
  },

  setupBookends: function() {
    var slider = this.el.getElement('.slider');
    var height = slider.getSize().y;
    var before = slider.clone();
    var after = slider.clone();
    before.removeClass('slider');
    before.addClass('bookend-before');
    before.setStyle('margin-top', -height);
    after.removeClass('slider');
    after.addClass('bookend-after');
    before.inject(this.el.getElement('.item'), 'before');
    after.inject(slider);
  },

  loadImages: function() {
    if (this.imageQueue.length > 0) {
      var imageHolder = this.imageQueue.shift();
      var itemNumber = imageHolder.retrieve('item-number');
      var itemClass = 'item' + itemNumber;
      var thumbHolder = this.el.getElement('.thumbs .' + itemClass);
      var holder = (itemNumber == 0) ? imageHolder : thumbHolder;
      var img = Asset.image(imageHolder.get('data-src'), {
        onLoad: function() {
          this.imageLoaded[itemNumber] = true;
          if (!this.isVisible) {
            this.isVisible = true;
            this.showHiddenElements();
            this.startInterval();
          }
          this.el.getElements('.' + itemClass).each(function(cloneHolder) {
            cloneHolder.removeClass(itemClass);
            cloneHolder.addClass('image-loaded');
            var imgClone = img.clone();
            imgClone.inject(cloneHolder);
          }.bind(this));
          img.fade('hide');
          holder.addClass('image-loaded');
          img.fade('in');
          this.loadImages();
        }.bind(this)
      });
      holder.removeClass(itemClass);
      img.inject(holder);
    }
  },

  setupInfo: function() {
    var info = this.getInfo();
    var infoBg = this.el.getElement('.info-bg');
    var resizeInfoBg = function() {
      var collapsedHeight = info.retrieve('collapsed-height');
      infoBg.setStyles({
        top: this.el.getSize().y - collapsedHeight,
        height: collapsedHeight
      });
    }.bind(this);
    resizeInfoBg();
    this.addEvent('resize', resizeInfoBg);
    var fxOptions = {
      duration: 500,
      transition: Fx.Transitions.Quart.easeOut,
      onComplete: function() {
        if (this.hover && !this.video) {
          this.showArrows();
        }
        this.infoIsShown = true;
        this.infoIsBeingShown = false;
      }.bind(this)
    };
    this.infoBgMorph = new Fx.Morph(infoBg, fxOptions);
  },

  setupArrows: function() {
    var next = this.el.getElement('.arrow-next');
    var prev = this.el.getElement('.arrow-prev');
    var repositionNextArrow = function() {
      next.setStyle('top', this.el.getSize().y);
    }.bind(this);
    this.addEvent('resize', repositionNextArrow);
    repositionNextArrow();
    var hoverStartEvent = 'mouseenter';
    var hoverEndEvent = 'mouseleave';
    if (isTouchUI()) {
      hoverStartEvent = 'touchstart';
      hoverEndEvent = 'touchend';
    }
    next.set('tween', this.options.arrowsFx);
    next.addEvent('click', function(e) {
      new Event(e).stop();
      if (!isTouchUI()) {
        if (this.isImageLoaded(this.index + 1)) {
          this.index++;
          this.rotate();
        }
      }
    }.bind(this));
    if (isTouchUI()) {
      next.addEvent('touchstart', function(e) {
        if (this.isImageLoaded(this.index + 1)) {
          this.index++;
          this.rotate();
        }
      }.bind(this));
    }
    next.addEvent(hoverStartEvent, function() {
      next.addClass('hover');
    });
    next.addEvent(hoverEndEvent, function() {
      next.removeClass('hover');
    });
    if (prev) {
      prev.set('tween', this.options.arrowsFx);
      prev.addEvent('click', function(e) {
        new Event(e).stop();
        if (!isTouchUI() && this.isImageLoaded(this.index - 1)) {
          this.index--;
          this.rotate();
        }
      }.bind(this));
      if (isTouchUI()) {
        prev.addEvent('touchstart', function(e) {
          if (this.isImageLoaded(this.index - 1)) {
            this.index--;
            this.rotate();
          }
        }.bind(this));
      }
      prev.addEvent(hoverStartEvent, function() {
        prev.addClass('hover');
      });
      prev.addEvent(hoverEndEvent, function() {
        prev.removeClass('hover');
      });
    }
  },

  setupEvents: function() {
    if (!isTouchUI()) {
      this.el.addEvent('mouseenter', this.hoverStart.bind(this));
      this.el.addEvent('mouseleave', this.hoverEnd.bind(this));
    }
  },

  shiftSlider: function() {
    var slider = this.el.getElement('.slider');
    var height = slider.getParent().getSize().y;
    if (this.index < -1 || this.index > this.count + 1) {
      var top = slider.getStyle('top').toInt();
      var offset = (this.index * -height) - top;
      this.index = this.index % this.count;
      slider.setStyle('top', (this.index * -height) - offset);
    }
  },

  getInfo: function() {
    var index = this.getNormalizedIndex();
    return this.el.getElements('.info')[index];
  },

  getNormalizedIndex: function(input) {
    if (!input) {
      input = this.index;
    }
    if (input < 0) {
      var index = this.count + input;
    } else {
      var index = input % this.count;
    }
    return index;
  },

  showHiddenElements: function() {
    this.timeMadeVisible = new Date().getTime();
    $$('.hidden-before-onload').each(function(el) {
      el.fade('hide');
      el.removeClass('hidden-before-onload');
      el.fade('in');
    });
  },

  hoverStart: function() {
    var now = new Date().getTime();
    if (this.timeMadeVisible != null &&
        now - this.timeMadeVisible < 1000) {
      this.hoverAfterLoad = true;
      this.el.addEvent('mousemove', function() {
        if (this.hoverAfterLoad) {
          this.hoverAfterLoad = false;
          this.hoverStart();
        }
      }.bind(this));
      return;
    }
    this.hover = true;
    if (!this.video) {
      this.showInfo();
      this.showThumbs();
      this.stopInterval();
    }
  },

  hoverEnd: function() {
    this.hover = false;
    if (!this.video) {
      this.hideInfo();
      this.hideThumbs();
      this.startInterval();
    }
  },

  setupItemVideo: function(item) {
    var playButton = new Element('div', {
      'class': 'video-play'
    }).inject(item);
    playButton.setStyle('opacity', 0.8);
    playButton.addEvent('mouseenter', function() {
      playButton.setStyle('opacity', 1.0);
    });
    playButton.addEvent('mouseleave', function() {
      playButton.setStyle('opacity', 0.8);
    });
    playButton.addEvent('click', function(e) {
      if (this.el.hasClass('video-paused')) {
        this.el.removeClass('video-paused');
        window.embed.resume();
      } else {
        new Event(e).stop();
        var src = item.get('data-video-src');
        this.playVideo(src, playButton);
        playButton.addClass('loading');
      }
    }.bind(this));
    var repositionPlayButton = function() {
      var height = this.el.getSize().y;
      playButton.setStyle('top', Math.round((height - 107) / 2));
    }.bind(this);
    this.addEvent('resize', repositionPlayButton);
  },

  setupItemTouchEvents: function(item) {
    var imageLink = item.getElement('.image-link');
    if (imageLink) {
      imageLink.addEvent('click', function(e) {
        e.stop();
        if (this.hover) {
          this.hoverEnd();
        } else {
          this.hoverStart();
        }
      }.bind(this));
    }
  },

  rotate: function() {
    if (this.el.getElement('.video-embed')) {
      this.video = null;
      this.el.removeClass('video-paused');
      this.el.getElement('.video-embed').destroy();
    }
    this.shiftSlider();
    this.sliderTween.cancel();
    this.sliderTween.start('top', this.index * -this.el.getSize().y);
    var currentInfo = this.el.getElement('.current-info');
    this.getContent(currentInfo).fade('out').retrieve('tween').chain(function() {
      currentInfo.removeClass('current-info');
      var info = this.getInfo();
      var content = this.getContent();
      if (this.hover) {
        info.setStyle('top', Math.round((this.el.getSize().y - info.getSize().y) / 2));
      } else {
        var collapsedHeight = info.retrieve('collapsed-height');
        this.infoBgMorph.start({
          top: this.el.getSize().y - collapsedHeight,
          height: collapsedHeight
        });
        info.setStyle('top', this.el.getSize().y - collapsedHeight);
      }
      info.addClass('current-info');
      content.fade('in');
    }.bind(this));
    var currentThumb = this.el.getElement('.current-thumb');
    currentThumb.getElement('.fade').fade('out');
    if (currentThumb.getElement('.title')) {
      currentThumb.getElement('.title').fade('in');
    }
    currentThumb.removeClass('current-thumb');
    var normalizedIndex = this.getNormalizedIndex();
    currentThumb = this.el.getElements('.thumbs a')[normalizedIndex];
    currentThumb.addClass('current-thumb');
    currentThumb.getElement('.fade').fade('in');
    if (currentThumb.getElement('.title')) {
      currentThumb.getElement('.title').fade('out');
    }
  },

  getContent: function(info) {
    if (!info) {
      info = this.getInfo();
    }
    return info.getElement('.content');
  },

  showInfo: function() {
    this.infoIsBeingShown = true;
    var info = this.getInfo();
    var containerHeight = this.el.getSize().y;
    var infoHeight = info.getSize().y;
    var tween = info.get('tween');
    tween.cancel();
    tween.start('top', Math.round((containerHeight - infoHeight) / 2));
    this.infoBgMorph.cancel();
    this.infoBgMorph.start({
      top: 0,
      height: containerHeight
    });
  },

  hideInfo: function() {
    this.infoIsShown = false;
    this.infoIsBeingShown = false;
    var info = this.getInfo();
    var tween = info.get('tween');
    var collapsedHeight = info.retrieve('collapsed-height');
    var collapsedPosition = this.el.getSize().y - collapsedHeight;
    tween.cancel();
    tween.start('top', collapsedPosition);
    this.infoBgMorph.cancel();
    this.infoBgMorph.start({
      top: collapsedPosition,
      height: collapsedHeight
    });
    this.hideArrows();
  },

  showArrows: function() {
    this.el.getElement('.arrow-prev').get('tween').cancel();
    this.el.getElement('.arrow-next').get('tween').cancel();
    this.el.getElement('.arrow-prev').tween('top', 0);
    this.el.getElement('.arrow-next').tween('top', this.el.getSize().y - 50);
  },

  hideArrows: function() {
    this.el.getElement('.arrow-prev').get('tween').cancel();
    this.el.getElement('.arrow-next').get('tween').cancel();
    this.el.getElement('.arrow-prev').setStyle('top', -50);
    this.el.getElement('.arrow-next').setStyle('top', this.el.getSize().y);
  },

  showThumbs: function() {
    var tween = this.el.getElement('.thumbs').get('tween');
    tween.cancel();
    tween.start('right', 0);
  },

  hideThumbs: function() {
    var tween = this.el.getElement('.thumbs').get('tween');
    tween.cancel();
    tween.start('right', -165);
  },

  stopInterval: function() {
    if (this.interval) {
      clearInterval(this.interval);
      this.interval = null;
    }
  },

  startInterval: function() {
    this.stopInterval();
    this.interval = setInterval(function() {
      this.index++;
      this.rotate();
    }.bind(this), this.options.sliderWaitDuration);
  },

  playVideo: function(src, playButton) {
    this.stopInterval();
    this.infoBgMorph.start({
      left: -320
    });
    var hideInfo = function() {
      this.infoBgMorph.start({
        left: -320
      });
      this.el.getElement('.arrow-prev').tween('left', -320);
      this.el.getElement('.arrow-next').tween('left', -320);
      this.el.getElement('.current-info').tween('left', -320);
      this.el.getElement('.thumbs').tween('right', -165);
    }.bind(this);
    var showInfo = function() {
      this.infoBgMorph.start({
        left: 0
      });
      this.el.getElement('.arrow-prev').tween('left', 0);
      this.el.getElement('.arrow-next').tween('left', 0);
      this.el.getElement('.current-info').tween('left', 0);
      this.el.getElement('.thumbs').tween('right', 0);
    }.bind(this);
    hideInfo();
    this.video = new Element('div', {
      'class': 'video-embed',
      html: '<div class="embed-box"><iframe src="' + src + '" name="embed" width="980" height="530" frameborder="0" allowfullscreen="allowfullscreen"></iframe></div>'
    }).inject(this.el);
    var timeout;
    var infoHidden = true;
    MoMA.addEvent('onMediaPlayerPlay', function() {
      playButton.removeClass('loading');
    }.bind(this));
    MoMA.addEvent('onMediaPlayerPause', function() {
      timeout = setTimeout(function() {
        infoHidden = false;
        showInfo();
        if (this.el.hasClass('video-complete')) {
          this.el.removeClass('video-complete');
        } else {
          this.el.addClass('video-paused');
        }
      }.bind(this), 2000);
    }.bind(this));
    MoMA.addEvent('onMediaPlayerResume', function() {
      if (timeout) {
        clearTimeout(timeout);
        timeout = null;
      }
      if (!infoHidden) {
        infoHidden = true;
        hideInfo();
        this.el.removeClass('video-paused');
      }
    }.bind(this));
    MoMA.addEvent('onMediaPlayerComplete', function() {
      this.el.addClass('video-complete');
    }.bind(this));
  },

  isImageLoaded: function(input) {
    input = this.getNormalizedIndex(input);
    return !!this.imageLoaded[input];
  }

});


MoMA.Features = new Class({

  rotatePeriod: 4500, // Switch an item in the grid every 4.5 seconds
  overlayDelay: 750,
  progressiveLoadDelay: 90000, // Load more collection items every 90 seconds */
  progressiveLoadChunkSize: 10,

  initialize: function(el, page) {

    this.el = el;
    this.page = page;
    this.visible = {};
    this.queue = []; // Used to rotate between hidden items
    this.hovered = false;

    this.addItems(el);
    this.setupRotation();

    $$('.size-1x3 h2.title').each(function(el) { el.shorten(79); });
    $$('.size-2x2 h2.title').each(function(el) { el.shorten(148); });

    if (this.queue.length > 0) {
      page.addEvent('onInitialize', this.startRotation.bind(this));
    }

    if (typeof progressiveLoadFeatures == 'object') {
      this.loadFeatures(progressiveLoadFeatures);
    }
  },

  setupRotation: function() {
    // This keeps track of where to rotate next
    this.rotateNum = 0;
    this.positions = this.queue.map(function(item) {
      if ($type(item) == 'element') {
        item = item.retrieve('item');
      }
      return item.position;
    });
    this.positions = this.positions.unique();
    this.positions.shuffle();
  },

  addItems: function(base) {
    base.getElements('div.feature, a.feature').each(function(el) {
      var feature = this.generateItem(el);
      if (el.hasClass('visible') || feature.rotateImages) {
        this.visible[feature.position] = feature;
      }
    }.bind(this));
  },

  generateItem: function(el) {
    if (el.getElement('.collection-feature')) {
      return new MoMA.Features.CollectionItem(el, this);
    } else {
      return new MoMA.Features.Item(el, this);
    }
  },

  startRotation: function() {
    if (this.page.featuresPauseRotation) {
      // This allows a flash element to take precedence at load time
      this.page.addEvent('onIntroComplete', this.startRotation.bind(this));
    } else {
      this.rotateInterval = this.rotateVisible.periodical(this.rotatePeriod, this);
    }

    // Preload the next item position
    var nextItem = this.getNextVisible(true);
    nextItem.loadImage();
  },

  hoverShow: function(target) {
    this.hovered = target;
  },

  hoverHide: function() {
    this.hovered = false;
  },

  rotateVisible: function() {
    if (MoMA.pause) {
      return;
    }
    var nextItem = this.getNextVisible();
    if (!nextItem) {
      return;
    }
    var grid = nextItem.grid;
    // We need to count down to ensure we're not looping forever
    var countdown = grid.queue.length;
    while (grid.visible[nextItem.position].isHovered() && countdown > 0) {
      grid.queue.push(nextItem);
      nextItem = this.getNextVisible();
      countdown--;
    }
    nextItem.coords = grid.visible[nextItem.position].coords;
    nextItem.show();

    // Preload the next item position
    nextItem = this.getNextVisible(true);
    nextItem.loadImage();
  },

  getNextVisible: function(justChecking) {
    var nextPosition = this.getNextPosition();
    var next = false;
    for (var i = 0; i < this.queue.length; i++) {
      next = this.queue[i];
      if (!justChecking) {
        if (this.qualifiesForNextRotation(next)) {
          this.queue.erase(next);
          break;
        } else {
          next = false;
        }
      }
    }
    return next;
  },

  getNextPosition: function() {
    return this.positions[this.rotateNum % this.positions.length];
  },

  qualifiesForNextRotation: function(item) {
    var nextPosition = this.getNextPosition();
    if (item.position == nextPosition && (!item.el.hasClass('visible') || item.rotateImages)) {
      this.rotateNum++;
      return true;
    }
    return false;
  },

  loadFeatures: function(index) {
    var chunkSize = this.progressiveLoadChunkSize;
    var urls = [];
    $H(index).each(function(indexes, position) {
      var queue = [];
      for (var i = 0; i < index[position].count; i++) {
        if (i != index[position].visible) {
          queue.push(i);
        }
      }
      queue.shuffle();
      while (queue.length > 0) {
        var ids = queue.slice(0, chunkSize);
        queue = queue.slice(chunkSize);
        urls.push('/features/' + position + '/' + ids.sort().join('/'));
      }
      this.positions.push(position);
    }.bind(this));
    this.loadFeaturesMarkup(urls);
  },

  loadFeaturesMarkup: function(urls) {
    if (urls.length > 0) {
      var url = urls.shift();
      var request = new Request({
        method: 'get',
        url: url,
        onComplete: function(html) {
          var holder = new Element('span', {
            styles: {
              display: 'none'
            }
          });
          holder.inject(this.el);
          holder.set('html', html);
          this.addItems(holder);
          holder.setStyle('display', 'inline');
          this.loadFeaturesMarkup.delay(this.progressiveLoadDelay, this, [urls]);
        }.bind(this)
      });
      request.send();
    }
  }

});

MoMA.Features.Item = new Class({

  Implements: [Events],

  initialize: function(el, grid) {
    if (el && grid) {
      this.el = el;
      this.grid = grid;
      this.color = el.getStyle('background-color');

      this.setupCaption();
      this.setupOutline();
      this.setupFx();
      this.setupPosition();
      this.setupEvents();
      this.setupGridQueue();
      this.setupImageLinks();
      this.setupMemberPreview();

      if (this.el.hasClass('visible')) {
        this.loadImage();
        this.assumeTallestRowHeight();
      }

      if (isIE7() || isIE6()) {
        var img = this.el.getElement('img');
        if (img) {
          img.addEvent('click', function() {
            window.location = el.get('href');
            return true;
          });
        }
      }

    }
  },

  loadImage: function(callback) {
    if (!this.isLoadable()) {
      return;
    }
    var img;
    if (this.rotateImages) {
      var src = this.pendingImages.pop();
      img = new Element('img', {
        src: src,
        'class': 'hidden',
        tween: this.imageTween
      });
    } else {
      img = new Element('img', {
        src: this.el.get('rel')
      });
    }
    if ($type(callback) == 'function') {
      img.addEvent('load', callback);
    }
    var target;
    if (this.el.getElement('.feature-images')) {
      target = this.el.getElement('.feature-images');
    } else {
      target = this.el.getElement('.holder');
    }
    img.inject(target);
    if (target.getElements('img').length == 1) {
      img.addClass('visible');
      img.removeClass('hidden');
    }
  },

  setupCaption: function() {
    if (this.isSlidable()) {
      this.el.getElement('.holder').addClass('bottom-caption');
      this.hasBottomCaption = true;
      this.caption = this.el.getElement('.caption');
      this.caption.set('tween', {
        duration: 500,
        transition: Fx.Transitions.Quart.easeOut
      });
      if (this.el.hasClass('visible')) {
        this.resetFill();
      } else {
        this.el.removeClass('hidden');
        this.resetFill();
        this.el.addClass('hidden');
      }
    }
  },

  setupOutline: function() {
    if (this.el.getElement('.outlined')) {
      var outline = new Element('span', {
        'class': 'outline'
      });
      outline.inject(this.el.getElement('.holder'));
    }
  },

  setupFx: function() {
    this.colorFx = new Fx.Tween(this.getColorFxTarget(), {
      duration: 500,
      transition: Fx.Transitions.Quart.easeOut
    });
    this.opacityFx = new Fx.Tween(this.el, {
      duration: 1000,
      transition: Fx.Transitions.Quart.easeOut,
      onStart: function() {
        this.el.addClass('transition');
      }.bind(this),
      onComplete: function() {
        this.grid.visible[this.position].hide();
        this.grid.visible[this.position] = this;
        this.el.removeClass('transition');
        this.el.addClass('visible');
        if (this.delayedMouseOver) {
          this.delayedMouseOver = false;
          this.mouseOver();
        }
      }.bind(this)
    });
  },

  getColorFxTarget: function() {
    return this.el;
  },

  setupPosition: function() {
    var col = this.el.className.match(/col-(\S+)/)[1];
    var row = this.el.className.match(/row-(\S+)/)[1];
    this.position = col + ',' + row;
    if (this.el.hasClass('visible')) {
      this.coords = this.el.getCoordinates(this.grid.el);
      this.setupHoverFill();
    } else if (this.grid.visible[this.position]) {
      this.coords = this.grid.visible[this.position].coords;
    }
  },

  setupEvents: function() {
    if (!this.el.getElement('.no-hover')) {
      this.el.addEvent('mouseenter', this.mouseOver.bind(this));
      this.el.addEvent('mouseleave', this.mouseOut.bind(this));
      var hover = this.el.getElement('.hover');
      if (hover) {
        hover.setStyles({
          border: '2px solid ' + this.color,
          width: this.coords.width - 4,
          height: this.coords.height - 4
        });
      }
    } else {
      this.el.getElement('.hover').destroy();
      this.el.getElement('.fill').destroy();
    }
  },

  setupGridQueue: function() {
    if (this.el.hasClass('hidden')) {
      this.rotateImages = false;
      this.grid.queue.push(this);
    } else if (this.el.getElement('.multiple-images')) {
      var link;
      if (this.el.getElement('.feature-images')) {
        link = this.el.getElement('.feature-images');
      } else {
        link = this.el;
      }
      this.rotateImages = true;
      this.grid.queue.push(this);
      this.pendingImages = link.get('rel').split(',');
      this.pendingImages.shuffle();
      this.imageTween = {
        duration: 1000,
        transition: Fx.Transitions.Quart.easeOut,
        onComplete: function() {
          this.hide();
        }.bind(this)
      };
      this.loadImage();
    }
  },

  setupHoverFill: function() {
    if (this.hoverFillIsSetup) {
      return;
    }
    this.hoverFillIsSetup = true;
    if (this.isSlidable()) {
      this.resetFill();
    }
  },

  setupImageLinks: function() {
    var linkedImages = this.el.getElements('a img');
    if (linkedImages.length > 0) {
      // This is slightly hacky. Instead the hover should be an anchor by default
      var hover = this.el.getElement('.hover');
      hover.setStyle('cursor', 'pointer');
      hover.addEvent('click', function() {
        window.location = linkedImages[0].getParent('a').get('href');
        return false;
      });
    }
  },

  setupMemberPreview: function() {
    var holder = this.el.getElement('.member-preview-exhibition');
    if (holder) {
      if (!holder.timeCheck()) {
        return;
      }
      var badge = new Element('span', {
        'class': 'member-preview',
        html: 'MEMBER PREVIEWS ON NOW'
      });
      if (holder.hasClass('ps1-exhibition')) {
        badge.addClass('member-preview-ps1');
        badge.set('html', 'AT <span class="hide">MoMA PS1</span>');
      } else if (holder.className.match(/preview(\d+)/)) {
        var previewClass = holder.className.match(/(preview\d+)/)[1];
        badge.addClass(previewClass);
      }
      badge.inject(this.el.getElement('.holder'));
      var controller = new MoMA.MemberPreviewBadge(badge);
      var showMemberPreviewLink = function() {
        badge.setStyle('opacity', 0);
        badge.setStyle('display', 'block');
        badge.fade('in');
      }.bind(this);
      if (this.el.hasClass('visible')) {
        if ($(document.body).hasClass('JS_Enabled')) {
          showMemberPreviewLink();
        } else {
          MoMA.addEvent('onInitialize', showMemberPreviewLink);
        }
      }
      this.addEvent('onShow', showMemberPreviewLink);
      this.addEvent('onHide', function() {
        badge.fade('out').retrieve('tween').chain(function() {
          badge.setStyle('display', 'none');
        });
      });
    }
  },

  mouseOver: function() {
    if (this.el.hasClass('transition')) {
      this.delayedMouseOver = true;
      return;
    }
    this.grid.hoverShow(this);
    this.el.addClass('hovered');
    if (this.isSlidable()) {
      this.slideFill();
    } else if (!this.isIntroduction()) {
      this.colorFx.start('background-color', '#FFF');
    }
  },

  mouseOut: function(e) {
    this.grid.hoverHide();
    this.el.removeClass('hovered');
    if (this.isSlidable()) {
      this.resetFill();
    } else {
      this.colorFx.cancel();
      var target = this.getColorFxTarget();
      target.setStyle('background-color', this.color);
    }
  },

  isHovered: function() {
    return this.el.hasClass('hovered');
  },

  isIntroduction: function() {
    return (this.el.hasClass('size-6x4'));
  },

  isSlidable: function() {
    return (this.hasCaption() && this.isLargish());
  },

  isLargish: function() {
    return (this.el.hasClass('size-4x4') || this.el.hasClass('size-2x4'));
  },

  isLoadable: function() {
    // Safari injects <noscript> tags into the DOM when progressive loading is
    // used, which confuses things.
    if (this.el.getElement('noscript')) {
      this.el.getElement('noscript').destroy();
    }
    return (!this.el.getElement('img') && !this.el.getElement('.no-image') ||
            this.pendingImages && this.pendingImages.length > 0);
  },

  hasCaption: function() {
    return ($type(this.el.getElement('.caption')) == 'element');
  },

  slideFill: function() {
    this.el.getElement('.fill').setStyle('top', 0);
  },

  resetFill: function() {
    var fill = this.el.getElement('.fill');
    var caption = this.el.getElement('.caption');
    var mainCaption = $$('.size-4x4.visible .caption');
    if (mainCaption.length > 0) {
      caption.setStyle('height', mainCaption[0].getSize().y - 20);
    }
    if (fill && caption) {
      fill.setStyle('top', this.el.getSize().y - caption.getSize().y);
    }
  },

  assumeTallestRowHeight: function() {
    var row = this.position.match(/.+,(\d+)$/)[1];
    var neighbors = $H(this.grid.visible).getKeys().filter(function(position) {
      return (position.substr(',' + row) !== -1);
    }.bind(this));
  },

  show: function(skipDelay) {
    if (!this.rotateImages) {
      this.el.setStyle('opacity', 0);
      this.el.removeClass('hidden');
      if (this.isSlidable()) {
        this.resetFill();
      }
      if (this.isLoadable()) {
        this.loadImage(this.fadeIn.bind(this));
      } else {
        this.fadeIn(skipDelay);
      }
    } else {
      var currImage = this.el.getElement('.visible');
      if (!currImage) {
        return;
      }
      currImage.setStyle('z-index', 2);
      this.prevImage = currImage;

      var nextImage = currImage.getNext('.hidden');
      if (!nextImage) {
        nextImage = this.el.getElement('.hidden');
      }
      if (nextImage) {
        nextImage.setStyles({
          'z-index': 3,
          opacity: 0
        });
        nextImage.removeClass('hidden');
        nextImage.addClass('visible');
        nextImage.tween('opacity', 1);
      }
    }
    this.fireEvent('onShow');
  },

  hide: function() {
    if (!this.rotateImages) {
      this.grid.queue.push(this);
      this.el.removeClass('visible');
      this.el.addClass('hidden');
    } else {
      this.prevImage.removeClass('visible');
      this.prevImage.addClass('hidden');
      this.grid.queue.push(this);
    }
    this.fireEvent('onHide');
  },

  fadeIn: function(skipDelay) {
    if (this.hasBottomCaption) {
      var delay = skipDelay ? 0 : this.grid.overlayDelay;
      this.caption.setStyle('opacity', 0);
      this.el.getElement('.fill').setStyle('opacity', 0);
      this.showCaption.delay(delay, this);
    }
    this.opacityFx.start('opacity', 1).chain(function() {
      this.setupHoverFill();
    }.bind(this));
  },

  /* ------------------ SETS OPACITY FOR HORIZONTAL FEATURE OVERLAY --------- */
  /* ------------------ ALSO IN #features .bottom-caption .fill IN GLOBAL.CSS --------- */
  showCaption: function() {
    if (this.caption) {
      this.caption.tween('opacity', 1);
      this.el.getElement('.fill').tween('opacity', 0.6);
    }
  }

});

MoMA.Features.CollectionItem = new Class({

  Extends: MoMA.Features.Item,

  initialize: function(el, grid) {
    this.parent(el, grid);
    this.setupExtraLink();
    this.el.getElement('.hover').destroy();
  },

  setupExtraLink: function() {
    var labels = this.el.getElements('.label');
    var collectionURL = '/explore/collection';
    var collectionFeature = this.el.getElement('.collection-feature');
    var objectURL = '/collection/browse_results.php?object_id=' + collectionFeature.get('data-objectid');
    var origUrl = this.el.get('href');
    labels.each(function(label) {
      label.addEvent('mouseenter', function() {
        var url = label.hasClass('orange') ? collectionURL : objectURL;
        this.el.addClass('label-hovered');
        label.addClass('label-is-hovered');
        this.el.set('href', url);
      }.bind(this));
      label.addEvent('mouseleave', function() {
        this.el.removeClass('label-hovered');
        label.removeClass('label-is-hovered');
        this.el.set('href', origUrl);
      }.bind(this));
    }.bind(this));
  }

});

MoMA.HomeFeatures = new Class({

  Extends: MoMA.Features,
  overlayDelay: 2000,
  skipExhibition: false,

  initialize: function(el, page) {
    this.parent(el, page);
    var initialPosition = this.positions[this.positions.length - 1];
    if (initialPosition != 'a,1' && this.visible[initialPosition].overlay) {
      this.visible[initialPosition].overlay.setStyle('opacity', 0);
      this.visible[initialPosition].showOverlay.delay(this.overlayDelay, this.visible[initialPosition]);
    }
    this.setupExhibitionsNav();
    page.addEvent('onIntroFade', function() {
      $('features').setStyle('visibility', 'visible');
    });
  },

  generateItem: function(el) {
    if (el.hasClass('col-a') && el.hasClass('row-1')) {
      var item = new MoMA.HomeFeatures.ExhibitionItem(el, this);
      el.store('object', item);
      return item;
    } else if (el.hasClass('col-e') && el.hasClass('row-1')) {
      return new MoMA.HomeFeatures.CollectionItem(el, this);
    } else {
      return new MoMA.Features.Item(el, this);
    }
  },

  getNextPosition: function() {
    var position = this.positions[this.rotateNum % this.positions.length];
    if (this.skipExhibition && position == 'a,1') {
      this.skipExhibition = false;
      this.rotateNum++;
      position = this.positions[this.rotateNum % this.positions.length];
    }
    return position;
  },

  setupExhibitionsNav: function() {
    var nav = new Element('div', {
        id: 'explore-nav',
        html: '<a href="#" class="prev">&lt;</a>' +
              '<a href="#" class="next">&gt;</a>' +
              '<br class="clear"/>',
        'class': 'hidden',
        events: {
          mouseenter: function() {
            this.el.addClass('exhibitions-nav-hovered');
            MoMA.pause = true;
          }.bind(this),
          mouseleave: function() {
            this.el.removeClass('exhibitions-nav-hovered');
            MoMA.pause = false;
          }.bind(this)
        }
    });
    nav.inject(this.el);
    nav.getElement('.prev').addEvent('click', this.prevExhibition.bind(this));
    nav.getElement('.next').addEvent('click', this.nextExhibition.bind(this));
    var exhibitions = this.el.getElements('.col-a.row-1');
    var prev = exhibitions.pop();
    var next = exhibitions[1];
    var loaded = 0;
    var callback = function() {
      loaded++;
      if (loaded == 2) {
        nav.removeClass('hidden');
      }
    };
    prev.retrieve('object').loadImage(callback);
    next.retrieve('object').loadImage(callback);
    this.setupLoadingIndicator();
  },

  prevExhibition: function() {
    var curr = this.el.getElement('.col-a.row-1.visible');
    var prev = this.getExhibition(curr, 'prev');
    if (prev.el.hasClass('transition')) {
      return false;
    }
    if (!prev.el.getElement('img') ||
        !prev.el.getElement('img').isLoaded()) {
      this.loadingEl.addClass('show');
      prev.loadImage(this.prevExhibition.bind(this));
      return false;
    }
    this.loadingEl.removeClass('show');
    prev.coords = curr.retrieve('object').coords;
    prev.show(true);
    prev = this.getExhibition(prev.el, 'prev');
    prev.loadImage();
    return false;
  },

  nextExhibition: function() {
    var curr = this.el.getElement('.col-a.row-1.visible');
    var next = this.getExhibition(curr, 'next');
    if (next.el.hasClass('transition')) {
      return false;
    }
    if (!next.el.getElement('img') ||
        !next.el.getElement('img').isLoaded()) {
      this.loadingEl.addClass('show');
      next.loadImage(this.nextExhibition.bind(this));
      return false;
    }
    this.loadingEl.removeClass('show');
    next.coords = curr.retrieve('object').coords;
    next.show(true);
    next = this.getExhibition(next.el, 'next');
    next.loadImage();
    return false;
  },

  getExhibition: function(origin, direction) {
    var el;
    if (direction == 'next') {
      el = origin.getNext('.col-a.row-1');
      if (!el) {
        el = this.el.getFirst('.col-a.row-1');
      }
    } else {
      el = origin.getPrevious('.col-a.row-1');
      if (!el) {
        el = this.el.getLast('.col-a.row-1');
      }
    }
    return el.retrieve('object');
  },

  setupLoadingIndicator: function() {
    this.loadingEl = new Element('div', {
      'id': 'exhibition-feature-loading'
    });
    this.loadingEl.setStyle('opacity', 0.4);
    this.loadingEl.inject($('page'));
  }

});


MoMA.HomeFeatures.CollectionItem = new Class({

  Extends: MoMA.Features.Item,

  initialize: function(el, grid) {
    this.parent(el, grid);
    this.setupExtraLink();
  },

  resetFill: function() {
    var mainCaption = this.grid.visible['a,1'].el.getElement('.caption');
    this.caption.setStyle('height', mainCaption.getSize().y - 20);
    (new MoMA.Features.Item()).resetFill.run([], this);
  },

  setupExtraLink: function() {
    var label = this.el.getElement('.label');
    var more = new Element('span', {
      'class': 'more',
      'html': '<span class="separator">|</span>' +
              '<span class="link">View all <span class="arrow">&raquo;</span></span>'
    });
    more.inject(label);
    var url = '/explore/collection/index';
    var link = more.getElement('.link');
    var origUrl = this.el.get('href');
    label.addEvent('mouseenter', function() {
      this.el.addClass('label-hovered');
      this.el.set('href', url);
    }.bind(this));
    label.addEvent('mouseleave', function() {
      this.el.removeClass('label-hovered');
      this.el.set('href', origUrl);
    }.bind(this));
  }

});

MoMA.HomeFeatures.ExhibitionItem = new Class({

  Extends: MoMA.Features.Item,

  initialize: function(el, grid) {
    this.parent(el, grid);
    if (el.getElement('.interactive')) {
      this.setupExtraLink('interactive');
    }
    this.setupExtraLink('label');
  },

  setupExtraLink: function(className) {
    var url = this.el.getElement('.' + className + ' .url').get('text');
    var link = this.el.getElement('.' + className + ' .link');
    var origUrl = this.el.get('href');
    if (className == 'label') {
      link = this.el.getElement('.label');
    }
    link.addEvent('mouseenter', function() {
      this.el.addClass(className + '-hovered');
      this.el.set('href', url);
    }.bind(this));
    link.addEvent('mouseleave', function() {
      this.el.removeClass(className + '-hovered');
      this.el.set('href', origUrl);
    }.bind(this));
  }

  /*mouseOut: function(e) {
    e = new Event(e);
    var related = $(e.relatedTarget);
    var parent = related.getParent('#explore-nav');
    if (related.get('id') == 'explore-nav' || parent) {
      return;
    }
    MoMA.pause = false;
    (new MoMA.Features.Item()).mouseOut.run([], this);
  }*/

});


MoMA.MultiPage = new Class({

  initialize: function(el) {
    this.el = el;
    this.slider = el.getElement('.slider');
    this.slider.set('tween', {
      duration: 750,
      transition: Fx.Transitions.Quart.easeOut
    });
    el.getElements('.pages a').each(function(link) {
      link.addEvent('click', this.clickLink.bind(this));
    }.bind(this));
  },

  clickLink: function(e) {
    e = new Event(e);
    e.preventDefault();

    this.el.getElement('.pages .selected').removeClass('selected');
    $(e.target).addClass('selected');
    this.slider.tween('left', $(e.target).get('rel'));
  }

});

MoMA.Sharing = new Class({

  initialize: function(el) {
    this.el = el;
    $('share-link').addEvent('click', this.toggle.bind(this));
  },

  toggle: function() {
    this.el.toggleClass('visible');
    return false;
  }

});

MoMA.HomeIntroduction = new Class({

  initialize: function(el, page) {
    // Disabling this for now
    if (true || window.location.search.contains('starts_here') ||
        Browser.Engine.trident ||
        window.location.search.contains('noflash') ||
        window.location.search.contains('starts_here') ||
        window.location.search.contains('nointro') ||
        window.location.hash.contains('txt') ||
        window.location.hash.contains('login') ||
        window.location.hash.contains('register') ||
        $(document.body).hasClass('nointro')) {
      if (window.location.search.contains('starts_here')) {
        $('features').setStyle('visibility', 'visible');
        overlay.addEvent('hide', function() {
          page.fireEvent('onIntroComplete');
        });
      } else {
        page.fireEvent('onIntroComplete');
        $('features').setStyle('visibility', 'visible');
      }
      return;
    }
    if (this.hasSeenIntroMovie() && !window.location.search.contains('flash') && !window.location.search.contains('intro')) {
      $('features').setStyle('visibility', 'visible');
      return;
    }
    Cookie.write('hasSeenIntroMovie', 'yes', {
    //each 0.1 is 6 min (0.3 / 18 = 12 min)
    //2 hours
      duration: 2 / 24
    });
    if ($('announcement')) {
      $('announcement').addClass('hidden');
    }
    $(document.body).addClass('intro-in-progress');
    page.addEvent('onIntroFade', function() {
      $(document.body).removeClass('intro-in-progress');
    });
    page.featuresPauseRotation = true;

    this.el = el;
    this.page = page;
    this.timeouts = [];

    var images = el.className.match(/(\d+)-images/);
    if (images) {
      var num = Math.ceil(Math.random() * parseInt(images[1], 10));
      if (document.referrer.contains('nytimes.com') || (new Date().format('%Y-%m-%d') == '2011-05-11')) {
        num = 7;
      }
      this.image = new Element('img', {
        src: 'http://' + this.getHostname() + '/images/intro/' + num + '.jpg',
        styles: {
          opacity: 0
        },
        events: {
          load: this.checkIfReady.bind(this),
          error: function() {
            this.finish();
          }.bind(this)
        }
      });
    } else {
      this.finish();
      return;
    }

    this.el.addEvent('click', function(e) {
      page.fireEvent('onIntroFade');
      this.finish();
    }.bind(this));

    this.context = new Element('div', {
      styles: {
        position: 'relative',
        width: 980,
        height: 530,
        overflow: 'hidden',
        cursor: 'pointer',
        'z-index': 97
      }
    }).inject(el);
    el.setStyles({
      position: 'absolute',
      top: 0,
      'z-index': 97
    });
    this.image.inject(this.context);

    this.momaText = new Element('img', {
      src: 'http://media.moma.org/images/intro/moma.png',
      styles: {
        position: 'absolute',
        top: 530,
        left: 0,
        'z-index': 100
      },
      events: {
        load: function() {
          if (!this.momaText.isLoaded()) {
            setTimeout(this.checkIfReady.bind(this), 0);
          } else {
            this.checkIfReady();
          }
        }.bind(this),
        error: function() {
          this.finish();
        }.bind(this)
      }
    });
    this.momaText.inject(this.context);

    el.removeClass('hidden');
  },

  hasSeenIntroMovie: function() {
    return Cookie.read('hasSeenIntroMovie');
  },

  checkIfReady: function() {
    if (!this.momaText) {
      return;
    }
    if (this.image.isLoaded() && this.momaText.isLoaded()) {
      this.slideMoMAText();
    }
  },

  slideMoMAText: function() {
    var newText = new Element('div', {
      id: 'home-intro-moma-text',
      styles: {
        position: 'absolute',
        top: 530,
        left: 0,
        'z-index': 100,
        width: 980,
        height: 530
      }
    });
    newText.inject(this.context);
    this.momaText.destroy();
    this.momaText = newText;
    this.momaText.set('tween', {
      duration: 733,
      transition: Fx.Transitions.Quint.easeOut // see: http://mootools.net/docs/core/Fx/Fx.Transitions
    });
    this.momaText.tween('top', 0).retrieve('tween').chain(function() {
      this.timeouts.push(this.slideStrip1.delay(267, this));
      this.timeouts.push(this.slideStrip2.delay(367, this));
      this.timeouts.push(this.slideStrip3.delay(467, this));
      this.timeouts.push(this.slideStrip4.delay(567, this));
      this.timeouts.push(this.slideStrip5.delay(667, this));
      this.timeouts.push(this.fadeRectangles.delay(5733, this));
    }.bind(this));
  },

  slideStrip1: function() {
    this.getStrip({
      top: -530,
      left: 680,
      width: 169
    }).tween('top', 0);
  },

  slideStrip2: function() {
    this.getStrip({
      top: 530,
      left: 510,
      width: 170
    }).tween('top', 0);
  },

  slideStrip3: function() {
    this.getStrip({
      top: -530,
      left: 340,
      width: 170
    }).tween('top', 0);
  },

  slideStrip4: function() {
    this.getStrip({
      top: 530,
      left: 170,
      width: 170
    }).tween('top', 0);
  },

  slideStrip5: function() {
    this.getStrip({
      top: -530,
      left: 0,
      width: 170
    }).tween('top', 0);
  },

  fadeRectangles: function() {
    var rectangles = [
      this.getRectangle({
        width: 330,
        height: 360,
        left: 0,
        top: 0
      }),
      this.getRectangle({
        width: 330,
        height: 360,
        left: 330,
        top: 91
      }),
      this.getRectangle({
        width: 330,
        height: 91,
        left: 330,
        top: 0
      }),
      this.getRectangle({
        width: 330,
        height: 170,
        left: 0,
        top: 360
      }),
      this.getRectangle({
        width: 330,
        height: 91,
        left: 660,
        top: 0
      }),
      this.getRectangle({
        width: 165,
        height: 270,
        left: 660,
        top: 91
      }),
      this.getRectangle({
        width: 330,
        height: 80,
        left: 330,
        top: 450
      }),
      this.getRectangle({
        width: 155,
        height: 270,
        left: 825,
        top: 91
      }),
      this.getRectangle({
        width: 320,
        height: 170,
        left: 660,
        top: 360
      })
    ];
    this.el.getElements('.strip').destroy();
    this.momaText.destroy();
    $('features').removeClass('hidden');
    var delay = 0;
    this.page.fireEvent('onIntroFade');
    if ($('announcement')) {
      $('announcement').fade('hide');
      $('announcement').removeClass('hidden');
      $('announcement').fade('in');
    }
    rectangles.each(function(rect, i) {
      this.timeouts.push((function () {
        rect.tween('opacity', 0);
        if (i == rectangles.length - 1) {
          this.finish.delay(333, this);
        }
      }).delay(delay, this));
      delay += 100;
    }.bind(this));
  },

  getStrip: function(styles) {
    var strip = new Element('div', {
      'class': 'strip',
      styles: $H({
        position: 'absolute',
        height: 530,
        background: 'transparent url(' + this.image.get('src') + ') no-repeat -' + styles.left + 'px 0',
        'z-index': 99
      }).combine(styles)
    });
    strip.set('tween', {
      duration: 367,
      transition: Fx.Transitions.Quint.easeOut
    });
    strip.inject(this.context);
    return strip;
  },

  getRectangle: function(styles) {
    var rectangle = new Element('div', {
      'class': 'rectangle',
      styles: $H({
        position: 'absolute',
        background: '#fff url(' + this.image.get('src') + ') no-repeat -' + styles.left + 'px -' + styles.top + 'px',
        'z-index': 101
      }).combine(styles)
    });
    var inner = new Element('div', {
      styles: {
        width: styles.width,
        height: styles.height,
        background: 'transparent url(http://media.moma.org/images/intro/moma.png) no-repeat -' + styles.left + 'px -' + styles.top + 'px',
        'z-index': 101
      }
    });
    rectangle.set('tween', {
      duration: 333,
      transition: Fx.Transitions.Linear
    });
    inner.inject(rectangle);
    rectangle.inject(this.context);
    return rectangle;
  },

  finish: function() {
    this.el.destroy();
    this.page.featuresPauseRotation = false;
    this.page.fireEvent('onIntroComplete');
    this.timeouts.each(function(timeout) {
      $clear(timeout);
    });
  },

  getHostname: function() {
    if (window.location.hostname == 'moma.org' || window.location.hostname == 'www.moma.org') {
      return 'media.moma.org';
    } else {
      return window.location.host;
    }
  }

});


MoMA.SectionTabs = new Class({

  initialize: function(el, page) {
    this.el = el;
    this.tabLinks = el.getElements('a');
    this.tabLinks.each(function(tabLink) {
      tabLink.addEvent('click', function(e) {
        e = new Event(e);
        var href = tabLink.get('href');
        var id = href.substr(href.indexOf('#') + 1);
        $$('.sectiontabs .selected')[0].removeClass('selected');
        $(e.target).addClass('selected');
        $$('.sectiontabs-content .selected')[0].removeClass('selected');
        $(id).addClass('selected');
        return false;
      });
    }.bind(this));
    this.page = page;
  }

});

MoMA.Collapsible = new Class({

  initialize: function(el, page) {
    this.el = el;
    this.page = page;

    var introModel = el.getElement('.intro');
    var introText = introModel.get('text');

    var titleLink = new Element('a', {
      href: '#',
      events: {
        click: this.toggle.bind(this)
      },
      styles: {
        outline: 'none'
      }
    });

    var titleModel = el.getElement('h4');
    var titleHeader = titleModel.clone();
    titleHeader.inject(titleLink);
    titleModel.destroy();

    titleLink.inject(el, 'top');

    var intro = new Element('span', {
      'class': 'excerpt',
      'text': introText
    });
    intro.inject(el);

    this.expander = new Element('a', {
      'href': '#',
      'text': '[+]',
      'class': 'expander',
      'events': {
        'click': this.toggle.bind(this)
      }
    });
    this.expander.inject(el);

    var details = el.getElement('.details');
    this.slide = new Fx.Slide(details).hide();
    details.setStyle('display', 'block');

    introModel.set('text', introText.replace('...', ''));
  },

  toggle: function() {
    this.el.toggleClass('expanded');
    if (this.expander.get('text') == '[+]') {
      this.expander.set('text', '[-]');
    } else {
      this.expander.set('text', '[+]');
    }
    this.slide.toggle();
    return false;
  }

});

MoMA.PerspectivesMenu = new Class({

  initialize: function(el, page) {
    el.addEvent('change', function() {
      window.location = el.options[el.selectedIndex].value;
    });
  }

});

MoMA.CollapsibleNav = new Class({

  initialize: function(el, page) {
    this.el = el;
    el.addEvent('mouseenter', this.showNav.bind(this));
    el.addEvent('mouseleave', this.hideNav.bind(this));
  },

  showNav: function() {
    this.el.fade('in');
  },

  hideNav: function() {
    this.el.fade('out');
  }

});

/*MoMA.DateInput = new Class({

  initialize: function(el, page) {
    this.el = el;
    new OverText([this.el]);
    this.picker = new DatePicker(this.el, {
      draggable: false,
      useDefaultCss: false,
      dayLabelLength: 1,
      groupNavLinks: true,
      wrapDayLinks: true,
      stickyWinOptions: {
        offset: {
          x: -10,
          y: 0
        },
        position: 'bottomLeft',
        className: 'datePicker'
      },
      stickyWinUiOptions: {
        css: '',
        cssClass: 'datePickerWindow'
      }
    });
  }

});*/

MoMA.Exhibitions = new Class({

  dayWidth: 5, /* Each day is 5 pixels wide */
  colors: ['#f0f0f0', '#7ac142'],
  labelHeight: 90,
  exhibitionHeight: 36,
  timelineHeight: 24,
  labelOffset: 14,

  highlightTitle: 'This week',
  highlightDays: 7,
  minSpan: ['month', 4],
  maxSpan: ['month', 6],

  initialize: function(el, page) {
    this.el = el;
    this.exhibitions = [];
    this.setupToday();
    this.setupTimespan();
    this.setupExhibitions();
    this.setupTimeline();
    this.arrangeExhibitions();
    this.replicateExhibitionTitles();
    this.highlight();
    $(document.body).addEvent('mousemove', this.moveHover.bind(this));
    window.exhibitions = this.exhibitions;
  },

  setupToday: function() {
    this.today = new Date().clearTime();
  },

  setupTimespan: function() {
    var origin = this.today.clone();
    this.min = origin.clone().decrement(this.minSpan[0], this.minSpan[1]).clearTime();
    this.max = origin.clone().increment(this.maxSpan[0], this.maxSpan[1] + 1).decrement('second', 1);
    this.dayRange = this.min.diff(this.max, 'day');
    this.timeRange = this.max.getTime() - this.min.getTime();
  },

  setupExhibitions: function() {
    this.el.getElements('.exhibition').each(function(el) {
      this.addExhibition(new this.Exhibition(el, this));
    }.bind(this));
    this.num = this.exhibitions.length;
  },

  setupTimeline: function() {

    this.exhibitionsHeight = this.num * this.exhibitionHeight;
    this.totalHeight = this.exhibitionsHeight + this.labelHeight + this.timelineHeight;

    var curr = this.min.clone();
    while (curr.diff(this.max, 'day') > 0) {
      var label = new Element('div', {
        text: this.getLabelTitle(curr),
        styles: {
          left: this.getPosition(curr) + 10
        }
      });
      label.inject($('timeline'));
      curr = this.addTickMark(curr);
    }
    curr = this.addTickMark(curr);

    $('timeline').setStyle('width', this.getPosition(this.max) + 20);
    this.totalWidth = this.getPosition(this.max, true);

    this.el.getElement('.holder').setStyles({
      width: this.totalWidth,
      height: this.totalHeight
    });
    this.el.getElement('.exhibitions-holder').setStyles({
      width: this.totalWidth,
      height: this.exhibitionsHeight
    });
    this.el.getElement('.backgrounds-holder').setStyles({
      width: this.totalWidth,
      height: this.exhibitionsHeight
    });

  },

  addTickMark: function(curr) {
    var tickMark = new Element('div', {
      'class': 'tick-mark',
      styles: {
        left: this.getPosition(curr, (curr.getMonth() == 2 && curr.getDate() == 3)),
        height: this.totalHeight - this.timelineHeight
      }
    });
    tickMark.inject(this.el.getElement('.holder'));
    return this.nextTickMark(curr);
  },

  nextTickMark: function(curr) {
    curr.set('date', 1);
    curr.set('month', curr.getMonth() + 1);
    return curr;
  },

  addExhibition: function(exhibition) {
    var exhibitionCutoff = this.today.clone().decrement('week', 2);
    if (exhibition.start < this.min) {
      if (exhibition.end < this.min || exhibition.end < exhibitionCutoff) {
        exhibition.el.destroy();
        return;
      }
      exhibition.start = this.min;
    }
    if (exhibition.end === false || exhibition.end > this.max) {
      if (exhibition.start > this.max) {
        exhibition.el.destroy();
        return;
      }
      exhibition.end = this.max;
    }
    var background = new Element('div', {
      'class': 'background',
      styles: {
        background: this.colors[this.exhibitions.length % this.colors.length]
      }
    });
    background.inject(this.el.getElement('.backgrounds-holder'));
    exhibition.background = background;
    this.exhibitions.push(exhibition);
  },

  arrangeExhibitions: function() {
    this.exhibitions.each(function(exhibition, num) {
      var start = this.getPosition(exhibition.start, num == 5);
      var end = this.getPosition(exhibition.end);
      exhibition.el.setStyles({
        left: start,
        top: num * this.exhibitionHeight
      });
      exhibition.background.setStyles({
        left: start,
        top: num * this.exhibitionHeight,
        width: end - start
      });
    }.bind(this));
    this.el.addClass('enabled');
  },

  replicateExhibitionTitles: function() {
    this.exhibitions.each(function(exhibition) {
      exhibition.replicateTitle();
    });
  },

  highlight: function() {
    var position = this.getPosition(this.today);
    var highlight = new Element('div', {
      'class': 'highlight',
      styles: {
        left: position,
        width: this.highlightDays * this.dayWidth,
        height: this.exhibitionsHeight + 8
      }
    });
    highlight.inject(this.el.getElement('.holder'));
    var scroll = new Fx.Scroll(this.el);
    scroll.set(this.getPosition(this.today) - 25, 0);
    $('highlight-label-top').set('text', this.highlightTitle);
    $('highlight-label-top').setStyle('left', this.getPosition(this.today) - this.labelOffset);
    $('highlight-label-bottom').setStyle('left', this.getPosition(this.today) - this.labelOffset);
    $('highlight-label-bottom').set('text', this.highlightTitle);
  },

  getLabelTitle: function(date) {
    var monthTitles = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                       'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return monthTitles[date.getMonth()] + ' ' +
           date.getFullYear().toString();
  },

  getPosition: function(date, interesting) {
    if (date === false) {
      date = this.max;
    }
    var total = this.dayRange * this.dayWidth;
    var pos = total * (date.getTime() - this.min.getTime()) / this.timeRange;
    return pos;
  },

  moveHover: function(e) {
    if (!this.hoverTarget) {
      return;
    }
    e = new Event(e);
    var height = $('hover').getSize().y;
    if (!height) {
      $('hover').setStyles({
        display: 'block',
        visibility: 'hidden',
        opacity: 0
      });
      height = $('hover').getSize().y;
      if (Browser.Engine.name != 'trident') {
        $('hover').fade('in');
      }
    }
    height = Math.max(height, 108);
    if (this.setHoverOrientation(e)) {
      $('hover').setStyles({
        display: 'block',
        visibility: 'visible',
        top: e.page.y - height - 24,
        left: e.page.x - $('page').getPosition().x - 5
      });
    } else {
      $('hover').setStyles({
        display: 'block',
        top: e.page.y - height - 24,
        left: e.page.x - $('page').getPosition().x - 5 - 370
      });
    }
  },

  setHoverOrientation: function(e) {
    if (e.page.x + 385 > window.getSize().x) {
      $('hover').addClass('left');
      return false;
    } else {
      $('hover').removeClass('left');
      return true;
    }
  },

  daysInMonth: function(date) {
    return 32 - new Date(date.getFullYear(), date.getMonth(), 32).getDate();
  },

  Exhibition: new Class({

    initialize: function(el, controller) {
      this.el = el;
      this.controller = controller;
      this.hover = el.clone();
      this.parseWhen();
      el.getElement('a').addEvent('mouseenter', this.showHover.bind(this));
      el.getElement('a').addEvent('mouseleave', this.hideHover.bind(this));
      this.hover.inject($('hover').getElement('.content'));
    },

    parseWhen: function(when) {
      var start = this.el.getElement('.start').get('text');
      var end = this.el.getElement('.end').get('text');
      if (end === '') {
        end = false;
      } else if (start == end) {
        end = Date.parse(parseInt(end, 10) * 1000).increment('day', 1);
      } else {
        end = Date.parse(parseInt(end, 10) * 1000);
      }
      this.start = Date.parse(parseInt(start, 10) * 1000);
      this.end = end;
      this.start.clearTime();
      if (this.end) {
        this.end.clearTime();
      }
    },

    replicateTitle: function() {
      var link = this.el.getElement('h3 a');
      var span = link.getElement('span');
      var replicaWidth;
      if (span.getSize().x < this.background.getSize().x) {
        link.setStyle('width', this.background.getSize().x);
        for (var replica, w = span.getSize().x; w < link.getSize().x; w += replicaWidth) {
          replica = span.clone();
          replica.addClass('replica');
          replica.inject(link);
          replicaWidth = replica.getSize().x + parseInt(replica.getStyle('margin-left'), 10);
        }
      }
      var clear = new Element('br', {
        'class': 'clear'
      });
      clear.inject(link);
    },

    showHover: function() {
      this.hover.setStyle('display', 'block');
      this.controller.hoverTarget = this;
      $('hover').fade('in');
    },

    hideHover: function(e) {
      this.hover.setStyle('display', 'none');
      if (this.controller.hoverTarget == this) {
        this.controller.hoverTarget = false;
      }
      $('hover').setStyle('display', 'none');
    }

  })

});

MoMA.FilmExhibitions = new Class({

  dayWidth: 137,
  labelOffset: 0,
  highlightDays: 1,
  highlightTitle: 'Today',
  minSpan: ['day', 15],
  maxSpan: ['day', 15],

  Extends: MoMA.Exhibitions,

  setupToday: function() {
    this.today = new Date().clearTime();
  },

  getLabelTitle: function(date) {
    var days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    var months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return days[date.getDay()] + ', ' + months[date.getMonth()] + ' ' + date.getDate();
  },

  nextTickMark: function(curr) {
    return curr.increment('day', 1).clearTime();
  }

});

MoMA.NavigationFeature = new Class({

  Implements: [Options, Events],

  options: {
    className: ''
  },

  initialize: function(slider, options) {
    this.slider = slider;
    this.setOptions(options);
    if (options.imageBorder) {
      this.options.className += ' border';
    }
    this.el = new Element('div', {
      'class': this.options.className + ' feature'
    });
    this.el.inject(slider);
  },

  setup: function(slider) {
    if (this.isSetup) {
      return;
    }
    this.isSetup = true;
    if (this.onPreSetup) {
      this.onPreSetup();
    }
    var template = this.options.template;
    this.el.set('html', template.substitute(this.options));
    if (this.onSetup) {
      this.onSetup();
    }
  }

});

MoMA.NavigationVideoFeature = new Class({

  Extends: MoMA.NavigationFeature,
  options: {
    className: 'video',
    label: 'VIDEO',
    template: '<div class="embed">{embed}</div>' +
              '<div class="nav-feature-info">' +
                '<div class="label"><a href="http://www.moma.org/explore/multimedia">{label}</a></div>' +
                '<div class="nav-feature-title"><a href="{href}">{title}</a></div>' +
              '</div>'
  },

  onPreSetup: function() {
    var url = this.options.href.replace('explore/multimedia/videos', 'videos/embed') + '?size=education-embed';
    this.options.embed = '<iframe src="' + url + '" width="378" height="283" frameborder="0" allowfullscreen="allowfullscreen"></iframe>'
  },

  onSetup: function() {
    var nav = $('nav-main').retrieve('controller');
    var subnav = this.el.getParent('.subnav');
    var id = subnav.retrieve('id');
    nav.addEvent(id + 'PageChange', function() {
      var src = this.el.getElement('iframe').src;
      this.el.getElement('iframe').src = src;
    }.bind(this));
  }

});

MoMA.NavigationImageFeature = new Class({

  Extends: MoMA.NavigationFeature,
  options: {
    className: 'image',
    maxWidth: 499,
    maxHeightOffset: 72,
    template: '<a href="{href}" class="image"></a>'
  },

  onSetup: function() {
    var holder = this.el.getElement('.image');
    var img = Asset.image(this.options.image, {
      onLoad: function() {
        img.inject(holder);
        img.setStyles({
          position: 'static',
          top: 'auto'
        });
        img.measure(function() {
          var maxHeight = this.el.getParent('nav.secondary').getSize().y - this.options.maxHeightOffset;
          var marginLeft = Math.round((this.options.maxWidth - img.getSize().x) / 2);
          var marginTop = Math.round((maxHeight - img.getSize().y) / 2);
          holder.setStyle('margin-left', marginLeft);
          holder.setStyle('margin-top', marginTop);
          this.el.fade('in');
        }.bind(this));
      }.bind(this),
      onError: function() {
        console.log("Error on Subnav load");
      }
    });
    img.setStyles({
      position: 'absolute',
      top: -1000000
    });
    img.inject(document.body);
    this.el.fade('hide');
    if (this.setupInfo) {
      this.setupInfo();
    }
  }

});


MoMA.NavigationImageTitleFeature = new Class({

  Extends: MoMA.NavigationImageFeature,
  options: {
    className: 'image',
    label: 'THE COLLECTION',
    labelHref: 'http://www.moma.org/explore/collection',
    maxWidth: 499,
    maxHeightOffset: 119,
    template: '<a href="{href}" class="image"></a>' +
              '<br class="clear" />' +
              '<div class="nav-feature-info">' +
                '<div class="label"><a href="{labelHref}">{label}</a></div>' +
                '<div class="nav-feature-title"><a href="{href}">{title}</a></div>' +
              '</div>'
  },

  setupInfo: function() {
    var title = this.el.getElement('.nav-feature-title');
    if (title.getSize().y > 20) {
      this.el.setStyle('margin-top', 20);
    }
  }

});

MoMA.NavigationSideImageFeature = new Class({

  Extends: MoMA.NavigationImageTitleFeature,
  options: {
    className: 'side-image image',
    label: 'PUBLICATIONS',
    labelHref: '/learn/publications',
    maxWidth: 280,
    maxHeightOffset: 72
  },

  setupInfo: function() {
    var holder = this.el.getElement('.nav-feature-info');
    holder.fade('hide');
    var maxHeight = this.el.getParent('nav.secondary').getSize().y;
    var top = Math.round((maxHeight - holder.getSize().y - this.options.maxHeightOffset) / 2);
    holder.setStyle('top', top);
    holder.fade('in');
  }

});

MoMA.NavigationSideImageDescriptionFeature = new Class({

  Extends: MoMA.NavigationSideImageFeature,
  options: {
    className: 'side-image-description side-image image',
    description: '',
    maxWidth: 280,
    template: '<a href="{href}" class="image"></a>' +
              '<br class="clear" />' +
              '<div class="nav-feature-info">' +
                '<div class="label"><a href="{labelHref}">{label}</a></div>' +
                '<div class="nav-feature-title"><a href="{href}">{title}</a></div>' +
                '<div class="nav-feature-description">{description}</div>' +
              '</div>'
  }

});


MoMA.MainNavigation = new Class({

  Implements: Events,

  initialize: function(el, controller) {
    this.el = el;
    el.store('controller', this);
    this.setupTouchHorizontalScrolling();
    if (!this.checkQuery()) {
      return;
    }
    this.preloadMaps();
    this.setupMapStyles();
    this.loadSubnavs();
    this.setupHoverEvents();
  },

  loadSubnavs: function() {
    var request = new Request.JSON({
      url: '/subnav.json',
      onComplete: function(response){
        MoMA.MainNavigation.navContent = response;
        this.fireEvent('navLoaded');
      }.bind(this)
    }).get();
  },

  setupHoverEvents: function() {
    $('nav-main-top').addClass('js-controlled-hover');
    this.el.getElements('#nav-main-top > ul > li').each(function(primaryItem) {
      primaryItem.addEvent('mouseenter', function() {
        if (!this.mouseLeaveTimeout) {
          this.showMenu(primaryItem);
        } else {
          if (primaryItem == this.mouseLeaveTarget) {
            clearTimeout(this.mouseLeaveTimeout);
            this.mouseLeaveTimeout = null;
          } else {
            this.mouseLeaveShowItem = primaryItem;
          }
        }
      }.bind(this));
      primaryItem.addEvent('mouseleave', function() {
        this.mouseLeaveTarget = primaryItem;
        this.mouseLeaveTimeout = setTimeout(function() {
          this.mouseLeaveTimeout = null;
          this.hideMenu(primaryItem);
          if (this.mouseLeaveShowItem) {
            this.showMenu(this.mouseLeaveShowItem);
            this.mouseLeaveShowItem = null;
          }
        }.bind(this), 100);
      }.bind(this));
    }.bind(this));
  },

  showMenu: function(primaryItem) {
    primaryItem.addClass('js-hover');
    var match = primaryItem.className.match(/(visit|explore|learn|support|shop|ps1)/);
    if (!match) {
      return;
    }
    var id = match[1];
    if (!this[id + 'IsSetup'] && this[id + 'Setup']) {
      this[id + 'IsSetup'] = true;
      this[id + 'Setup']();
    }
    this.fireEvent('showMenu', id);
  },

  hideMenu: function(primaryItem) {
    primaryItem.removeClass('js-hover');
    this.fireEvent('hideMenu');
  },

  checkQuery: function() {
    var navParam = location.search.match(/nav=(hide|show|top|bottom)/);
    if (navParam) {
      Cookie.write('nav', navParam[1], {
        path: '/'
      });
    }
    if (location.search.match(/nav=hide/) ||
        Cookie.read('nav') == 'hide' ||
        $(document.body).hasClass('nav-hidden')) {
      this.el.setStyle('display', 'none');
      $(document.body).addClass('nav-hidden');
      return false;
    } else if ((Browser.Platform.ipod || Browser.Platform.ios || Browser.Platform.android) && !navigator.userAgent.match(/iPad/i)) {
      this.reduced = true;
      Asset.css('/stylesheets/reduced-nav.css');
      /*this.el.getElements('nav.secondary').each(function(nav) {
        new Element('div', {
          'class': 'right-shadow'
        }).inject(nav);
      });*/
      this.el.setStyle('display', 'block');
      return false;
    } else {
      this.el.setStyle('display', 'block');
      return true;
    }
  },

  setupMapStyles: function() {
    this.mapStyles = [
      {
        "featureType": "administrative.land_parcel",
        "stylers": [
          { "visibility": "off" }
        ]
      },{
        "featureType": "administrative.province",
        "stylers": [
          { "visibility": "off" }
        ]
      },{
        "featureType": "administrative.country",
        "stylers": [
          { "visibility": "off" }
        ]
      },{
        "featureType": "poi.attraction",
        "stylers": [
          { "visibility": "off" }
        ]
      },{
        "featureType": "poi.business",
        "stylers": [
          { "visibility": "off" }
        ]
      },{
        "featureType": "poi.government",
        "stylers": [
          { "visibility": "off" }
        ]
      },{
        "featureType": "poi.medical",
        "stylers": [
          { "visibility": "off" }
        ]
      },{
        "featureType": "poi.place_of_worship",
        "stylers": [
          { "visibility": "off" }
        ]
      },{
        "featureType": "poi.school",
        "stylers": [
          { "visibility": "off" }
        ]
      },{
        "featureType": "poi.sports_complex",
        "stylers": [
          { "visibility": "off" }
        ]
      },{
        "featureType": "road.arterial",
        "elementType": "geometry.fill",
        "stylers": [
          { "saturation": -100 },
          { "lightness": 100 }
        ]
      },{
        "featureType": "road.arterial",
        "elementType": "geometry",
        "stylers": [
          { "saturation": -100 },
          { "lightness": 26 }
        ]
      },{
        "elementType": "geometry.fill"	  },{
        "elementType": "geometry.stroke",
        "stylers": [
          { "saturation": -100 }
        ]
      },{
        "featureType": "road.arterial",
        "elementType": "labels.text.stroke",
        "stylers": [
          { "saturation": -100 },
          { "lightness": 100 }
        ]
      },{
      },{
        "elementType": "labels.text.fill",
        "stylers": [
          { "saturation": -100 }
        ]
      },{
        "elementType": "labels.text.stroke",
        "stylers": [
          { "saturation": -100 }
        ]
      },{
        "featureType": "landscape.man_made",
        "elementType": "geometry",
        "stylers": [
          { "lightness": 21 },
          { "saturation": -100 },
          { "visibility": "off" }
        ]
      },{
        "featureType": "transit.station.bus",
        "stylers": [
          { "visibility": "off" }
        ]
      },{
        "featureType": "road.highway",
        "elementType": "geometry.fill",
        "stylers": [
          { "lightness": 90 },
          { "saturation": -100 }
        ]
      },{
        "featureType": "road.highway",
        "elementType": "geometry.stroke",
        "stylers": [
          { "lightness": 25 },
          { "saturation": -100 }
        ]
      },{
        "featureType": "road.highway",
        "elementType": "labels.text.stroke",
        "stylers": [
          { "lightness": 90 }
        ]
      },{
        "featureType": "water",
        "elementType": "labels.text.stroke",
        "stylers": [
          { "saturation": -70 },
          { "lightness": -25 }
        ]
      },{
        "featureType": "landscape.natural",
        "elementType": "geometry.fill",
        "stylers": [
          { "saturation": -100 }
        ]
      },{
        "featureType": "landscape.natural",
        "stylers": [
          { "saturation": -100 }
        ]
      },{
        "featureType": "administrative",
        "stylers": [
          { "saturation": -100 }
        ]
      },{
        "featureType": "transit.line",
        "stylers": [
          { "visibility": "off" }
        ]
      },{
        "featureType": "transit.station.airport",
        "stylers": [
          { "saturation": -100 },
          { "visibility": "on" }
        ]
      },{
        "elementType": "geometry.fill"	  },{
        "featureType": "poi.park",
        "elementType": "geometry.fill",
        "stylers": [
          { "hue": "#aaff00" },
          { "lightness": -5 }
        ]
      },{
        "featureType": "poi.park",
        "elementType": "labels",
        "stylers": [
          { "saturation": -100 }
        ]
      },{
        "featureType": "road.highway",
        "elementType": "labels.icon",
        "stylers": [
          { "saturation": -100 },
          { "gamma": 0.75 },
          { "visibility": "off" }
        ]
      },{
        "elementType": "labels",
        "stylers": [
          { "saturation": -100 }
        ]
      },{
        "featureType": "road.highway.controlled_access",
        "elementType": "labels.icon",
        "stylers": [
          { "visibility": "off" }
        ]
      },{
        "featureType": "road.arterial",
        "elementType": "labels.icon",
        "stylers": [
          { "visibility": "off" }
        ]
      },{
        "featureType": "administrative.neighborhood",
        "elementType": "labels.text",
        "stylers": [
          { "visibility": "off" }
        ]
      }
    ];
  },

  setupLogo: function() {
    if (this.showLogo()) {
      Cookie.write('logo-shown', true);
      var div = new Element('div', {
        id: 'side-logo'
      }).inject(document.body);
      var resize = function() {
        var width = window.getSize().x;
        var margin = (width - 980) / 2;
        var gutter = (width < 1370) ? 17 : 16;
        div.setStyle('left', 980 + margin + gutter);
      };
      resize();
      window.addEvent('resize', resize);
      window.addEvent('scroll', function() {
        if (window.getScroll().y > 20 && !$('side-logo').hasClass('fixed')) {
          $('side-logo').addClass('fixed');
        } else if (window.getScroll().y <= 20 && $('side-logo').hasClass('fixed')) {
          $('side-logo').removeClass('fixed');
        }
      });
    }
  },

  preloadMaps: function() {
    var visitMap = (window.devicePixelRatio > 1) ? 'visit-map-loading_2x.jpg' : 'visit-map-loading.jpg';
    var ps1Map = (window.devicePixelRatio > 1) ? 'ps1-map-loading_2x.jpg' : 'ps1-map-loading.jpg';
    new Element('div', {
      id: 'nav-preload',
      html: ('<img src="/images/nav/{visitMap}" id="nav-visit-map-loading" width="460" height="294" class="loading" />' +
             '<img src="/images/nav/{ps1Map}" id="nav-ps1-map-loading" width="260" height="250" class="loading" />').substitute({
        visitMap: visitMap,
        ps1Map: ps1Map
      })
    }).inject($('nav-main'));
  },

  showLogo: function() {
    if ($(document.body).hasClass('no-side-logo')) {
      return false;
    } else if (window.location.pathname == '/') {
      return true;
    } else if (!Cookie.read('logo-shown')) {
      return true;
    } else {
      return false;
    }
  },

  visitSetup: function() {
    var subnav = this.createSubnav('visit',
      '<div class="visit-map"></div>' +
      '<div class="visit-info">' +
        '<a href="/visit/plan/gettinghere" class="address">11 West 53 Street&nbsp; New York, NY 10019</a>' +
        '<span id="nav-hours"></span>' +
      '</div>'
    );
    this.visitSetupHours();
    var map = subnav.getElement('.visit-map');
    $('nav-visit-map-loading').setStyles({
      position: 'absolute',
      left: map.getPosition(subnav).x,
      top: map.getPosition(subnav).y
    });
    $('nav-visit-map-loading').inject(subnav);
    $('nav-visit-map-loading').set('tween', {
      duration: 250,
      transition: Fx.Transitions.Quart.easeOut,
      onComplete: function() {
        $('nav-visit-map-loading').inject($('nav-preload'));
      }
    });
    if (!google.maps) {
      google.load('maps', '3.x', {
        callback: this.visitSetupMap.bind(this),
        other_params: 'sensor=false'
      });
    } else {
      this.visitSetupMap();
    }
  },

  visitSetupHours: function() {
    $('nav-main').getElement('.visit-info').set('tween', {
      duration: 500,
      transition: Fx.Transitions.Quart.easeOut
    });
    $('nav-main').getElement('.visit-info').fade('hide');
    new Request.JSON({
      url: '/hours.json',
      onComplete: function(response) {
        if (response.closed) {
          $('nav-hours').addClass('closed');
          $('nav-hours').set('html', 'The Museum is closed today.');
        } else {
          var hours = '<a href="/visit/plan">Today’s hours: {open_time}&ndash;{closed_time}</a>'.substitute(response)
          $('nav-hours').set('html', hours);
        }
        $('nav-main').getElement('.visit-info').fade('in');
      }
    }).get();
  },

  visitSetupMap: function() {
    var mapDiv = this.el.getElement('.visit-map');
    var relHeight = $('nav-main').getElement('.visit .nav-relative').getSize().y;
    mapDiv.setStyle('height', relHeight - 72);
    this.visitMap = new google.maps.Map(mapDiv, {
      zoom: 16,
      center: new google.maps.LatLng(40.76178051355846, -73.97807112037658),
      mapTypeId: google.maps.MapTypeId.ROADMAP,
      mapTypeControlOptions: {
        mapTypeIds: ['minimal']
      },
      mapTypeId: 'minimal',
      streetViewControl: false,
      mapTypeControl: false
    });
    google.maps.event.addListenerOnce(this.visitMap, 'tilesloaded', function() {
      setTimeout(function() {
        $('nav-visit-map-loading').fade('out');
      }, 250);
    });
    this.visitMap.mapTypes.set('minimal', new google.maps.StyledMapType(this.mapStyles, {
      name: "Minimal"
    }));
    var momaMarker = {
      latlng: new google.maps.LatLng(40.76128480433553, -73.9777170687866),
      origin: new google.maps.Point(971, 7),
      anchor: new google.maps.Point(8, 74),
      size: new google.maps.Size(39, 74)
    };
    this.setupMapMarker(this.visitMap, momaMarker);
    this.addEvent('showMenu', function(id) {
      if (id == 'visit') {
        google.maps.event.trigger(this.visitMap, 'resize');
      }
    }.bind(this));
  },

  exploreSetup: function() {
    this.dynamicSetup('explore');
  },

  learnSetup: function() {
    this.dynamicSetup('learn');
  },

  supportSetup: function() {
    this.dynamicSetup('support');
  },

  shopSetup: function() {
    this.dynamicSetup('shop');
  },

  dynamicSetup: function(id) {
    if (!MoMA.MainNavigation.navContent) {
      this.addEvent('navLoaded', function() {
        this.dynamicSetup(id);
      }.bind(this));
      return;
    }
    var subnav = this.createSubnav(id, '<div class="slider"></div>');
    var slider = subnav.getElement('.slider');
    var items = this.loadItems(id, slider);
    slider.setStyle('width', items.length * 499);
    if (items.length == 0) {
      this.showSubnavErrorMessage(id);
    } else {
      items[0].setup();
      this.createPagination(subnav, items);
    }
  },

  ps1Setup: function() {
    var subnav = this.el.getElement('.ps1 nav.secondary');
    var map = this.el.getElement('.ps1-map');
    $('nav-ps1-map-loading').setStyles({
      position: 'absolute',
      left: map.getPosition(subnav).x,
      top: map.getPosition(subnav).y
    });
    $('nav-ps1-map-loading').inject(subnav);
    $('nav-ps1-map-loading').set('tween', {
      duration: 250,
      transition: Fx.Transitions.Quart.easeOut,
      onComplete: function() {
        $('nav-ps1-map-loading').inject($('nav-preload'));
      }
    });
    if (!google.maps) {
      google.load('maps', '3.x', {
        callback: this.ps1SetupMap.bind(this),
        other_params: 'sensor=false'
      });
    } else {
      this.ps1SetupMap();
    }
  },

  ps1SetupMap: function() {
    var mapDiv = this.el.getElement('.ps1-map');
    this.ps1Map = new google.maps.Map(mapDiv, {
      zoom: 12,
      center: new google.maps.LatLng(40.758643668288265, -73.96140923797607),
      mapTypeId: google.maps.MapTypeId.ROADMAP,
      mapTypeControlOptions: {
        mapTypeIds: ['minimal']
      },
      mapTypeId: 'minimal',
      streetViewControl: false,
      mapTypeControl: false
    });
    google.maps.event.addListenerOnce(this.ps1Map, 'tilesloaded', function() {
      setTimeout(function() {
        $('nav-ps1-map-loading').fade('out');
      }, 250);
    });
    this.ps1Map.mapTypes.set('minimal', new google.maps.StyledMapType(this.mapStyles, {
      name: "Minimal"
    }));
    var momaMarker = {
      latlng: new google.maps.LatLng(40.76128480433553, -73.9777170687866),
      origin: new google.maps.Point(971, 7),
      anchor: new google.maps.Point(8, 74),
      size: new google.maps.Size(39, 74)
    };
    var ps1Marker = {
      latlng: new google.maps.LatLng(40.745599, -73.948148),
      origin: new google.maps.Point(899, 7),
      anchor: new google.maps.Point(26, 38),
      size: new google.maps.Size(60, 38)
    };
    this.setupMapMarker(this.ps1Map, momaMarker);
    this.setupMapMarker(this.ps1Map, ps1Marker);
    this.addEvent('showMenu', function(id) {
      if (id == 'ps1') {
        google.maps.event.trigger(this.ps1Map, 'resize');
      }
    }.bind(this));
  },

  setupMapMarker: function(map, marker) {
    var spriteURL = '/images/common/ui-2x.png';
    var scaledSize = new google.maps.Size(1228, 116);
    var icon = new google.maps.MarkerImage(spriteURL, marker.size, marker.origin, marker.anchor, scaledSize);
    var marker = new google.maps.Marker({
      position: marker.latlng,
      map: map,
      icon: icon
    });
  },

  createPagination: function(subnav, items) {
    if (items.length < 2) {
      return;
    }
    var html = '';
    for (var i = 0; i < items.length; i++) {
      if (i == 0) {
        html += '<a href="#" class="selected page"></a>';
      } else {
        html += '<a href="#" class="page"></a>';
      }
    }
    var el = new Element('div', {
      'class': 'nav-pagination',
      html: html
    });
    el.inject(subnav.getParent('.nav-relative'));
    var slider = subnav.getElement('.slider');
    slider.set('tween', {
      duration: 500,
      transition: Fx.Transitions.Quint.easeOut
    });
    var id = subnav.retrieve('id', id);
    var current = 0;
    var selectPage = function(index) {
      this.fireEvent(id + 'PageChange');
      current = index;
      slider.tween('left', -499 * index);
      items[index].setup();
      el.getElement('.page.selected').removeClass('selected');
      el.getElements('.page')[index].addClass('selected');
    }.bind(this);
    el.getElements('.page').each(function(link, index) {
      link.addEvent('click', function(e) {
        new Event(e).stop();
        selectPage(index);
      }.bind(this));
    }.bind(this));
    var prev = new Element('a', {
      href: '#',
      'class': 'nav-prev',
      html: '<span class="nav-icon"></span>'
    }).inject(subnav);
    var next = new Element('a', {
      href: '#',
      'class': 'nav-next',
      html: '<span class="nav-icon"></span>'
    }).inject(subnav);
    prev.addEvent('click', function(e) {
      new Event(e).stop();
      current--;
      if (current < 0) {
        current = items.length - 1;
      }
      selectPage(current);
    });
    next.addEvent('click', function(e) {
      new Event(e).stop();
      selectPage((current + 1) % items.length);
    });
    el.setStyle('right', Math.floor((499 - el.getSize().x) / 2));
    return el;
  },

  createPaginationArrows: function(subnav) {
    var id = subnav.retrieve('id', id);

  },

  createSubnav: function(id, html, options) {
    if (!options) {
      options = {};
    }
    var relative = new Element('div', {
      'class': 'nav-relative'
    });
    var subnav = new Element('div', {
      'class': 'subnav',
      html: html.substitute(options)
    });
    subnav.store('id', id);
    var secondary = this.el.getElement('li.' + id + ' nav.secondary');
    relative.inject(secondary, 'top');
    subnav.inject(relative);
    subnav.setStyle('height', secondary.getSize().y - 9);
    relative.setStyle('height', secondary.getSize().y - 9);
    return subnav;
  },

  loadItems: function(id, slider) {
    var items = [];
    var section = MoMA.MainNavigation.navContent[id];
    if (section) {
      section.each(function(item) {
        var itemClass = 'Navigation' + item.featureType + 'Feature';
        items.push(new MoMA[itemClass](slider, item));
      });
    }
    return items;
  },

  showSubnavErrorMessage: function(section) {
    var subnav = this.el.getElement('.' + section + ' .subnav');
    subnav.set('html', '<div class="error-message">There was a problem loading the navigation. We apologize for any inconvenience.</div>');
  },

  setupTouchHorizontalScrolling: function() {
    if (!isTouchUI()) {
      return;
    }
    this.touchDrag = false;
    this.touchOffset = 0;
    this.el.addEvent('touchstart', function(e) {
      this.startZoom = document.documentElement.clientWidth / window.innerWidth;
      this.touchDrag = true;
      this.touchOrigin = this.touchOffset;
      this.touchStart = e.touches[0].clientX;
    }.bind(this));
    document.body.addEvent('touchend', function(e) {
      this.touchDrag = false;
      var zoom = document.documentElement.clientWidth / window.innerWidth;
      if (this.startZoom - zoom > 0.1) {
        this.el.setStyle('margin-left', 0);
      }
    }.bind(this));
    this.el.addEvent('touchmove', function(e) {
      if (this.touchDrag) {
        e.stop();
        var marginLeft = this.touchOrigin + e.touches[0].clientX - this.touchStart;
        marginLeft = Math.min(marginLeft, 0);
        this.touchOffset = marginLeft;
        this.el.setStyle('margin-left', marginLeft);
      }
    }.bind(this));
  }

});

MoMA.HomeSponsorship = new Class({

  initialize: function(el, page) {
    this.el = el;
    if (page.heroImagesAreSetup) {
      this.setup();
    } else {
      page.addEvent('heroImagesSetup', this.setup.bind(this));
    }
  },

  setup: function() {
    this.items = this.el.getElements('.sponsor');
    this.index = Math.floor(Math.random() * this.items.length);
    setTimeout(this.showImage.bind(this), 2000);
  },

  showImage: function() {
    var item = this.items[this.index];
    var showNextImage = function() {
      item.fade('hide');
      item.addClass('fade-in');
      item.fade('in').retrieve('tween').chain(function() {
        var current = this.el.getElement('.current');
        if (current) {
          current.removeClass('current');
        }
        item.addClass('current');
        item.removeClass('fade-in');
      }.bind(this));
      if (!this.interval) {
        this.interval = setInterval(this.rotate.bind(this), 8000);
      }
    }.bind(this);
    var img = item.getElement('img');
    if (!img) {
      img = Asset.image(item.get('data-src'), {
        onLoad: showNextImage
      }).inject(item);
    } else {
      showNextImage();
    }
  },

  rotate: function() {
    this.index = (this.index + 1) % this.items.length;
    this.showImage();
  }

});

MoMA.HomeEvents = new Class({

  initialize: function(el) {
    var link = $('visit').getElement('.show-events');
    link.addEvent('click', function(e) {
      new Event(e).stop();
      el.addClass('show-events');
      link.getParent().destroy();
    });
  }

});

MoMA.Tribute = new Class({

  initialize: function(el) {
    /*this.slide = new Fx.Slide($('tribute-details'), {
      duration: 1000
    });
    if ($('honor_flag_y').checked) {
      $('tribute').addClass('visible');
      this.slide.show();
    } else {
      $('tribute').removeClass('visible');
      this.slide.hide();
    }
    this.el = el;
    */
    $('honor_flag_y').addEvent('click', this.onChange.bind(this));
    $('honor_flag_n').addEvent('click', this.onChange.bind(this));
    if ($('honor_flag_y').checked) {
      $('tribute').addClass('visible');
    } else {
      $('tribute').removeClass('visible');
    }
  },

  onChange: function() {
    /*
    if ($('tribute').hasClass('visible')) {
      this.slide.toggle().chain(function() {
        $('tribute').toggleClass('visible');
      });
    } else {
      $('tribute').toggleClass('visible');
      this.slide.toggle();
    }
    */
    if ($('honor_flag_y').checked) {
      $('tribute').addClass('visible');
    } else {
      $('tribute').removeClass('visible');
    }
  }

});

MoMA.SocialBar = new Class({

  initialize: function(el) {
    this.expanded = false;
    $('social').set('tween', {
      duration: 500,
      transition: Fx.Transitions.Quint.easeOut
    });
    el.addEvent('click', function() {
      if (!this.expanded) {
        $('social').setStyle('background-image', 'none');
        $('social').tween('height', 300);
      } else {
        $('social').setStyle('background-image', 'url(/new/images/nav/perspectives.png)');
        $('social').tween('height', 25);
      }
      this.expanded = !this.expanded;
    }.bind(this));
  }

});

MoMA.MembershipOptions = new Class({

  initialize: function(el) {
    this.el = el;
    this.setupCategories();
    this.setupMemberInfo();
  },

  setupCategories: function() {
    var links = this.el.getElements('.option a');
    var details = this.el.getElements('.option .details');
    this.accordion = new Accordion(links, details, {
      show: this.getInitialView(),
      onActive: function(toggler, element) {
        if (this.active) {
          this.active.setStyle('height', $(this.active).getSize().y);
        }
        this.active = $(element);
        return false;
      }.bind(this),
      onComplete: function() {
        this.active.setStyle('height', 'auto');
      }.bind(this)
    });

    if (this.el.getElement('.gift').hasClass('selected') &&
        this.el.getElement('.message')) {
      this.el.getElement('.message').fade('hide');
    }

    links.each(function(link) {
      link.addEvent('click', this.chooseOption.bind(this));
    }.bind(this));
    details.each(function(details) {
      details.addClass('visible');
    }.bind(this));
  },

  getInitialView: function() {
    if ($('visible')) {
      var visible = $('visible').value;
      if (this.el.getElement('.option.' + visible)) {
        var options = this.el.getElements('.option');
        for (var i = 0; i < options.length; i++) {
          if (options[i].hasClass(visible)) {
            scroller = new Fx.Scroll(window);
            scroller.toElement(options[i]);
            return i;
          }
        }
      }
    }
    return 'all-close';
  },

  setupMemberInfo: function() {
    var slide = new Fx.Slide(this.el.getElement('.member-info'));
    if (!$('member-checkbox').checked) {
      slide.hide();
    }
    $('member-checkbox').addEvent('click', function() {
      slide.toggle();
    });
  },

  chooseOption: function(e) {
    e = new Event(e);
    if ($(e.target.parentNode).hasClass('me')) {
      $('membership_type').value = 'self';
      if (this.el.getElement('.message')) {
        this.el.getElement('.message').fade('in');
      }
    } else if ($(e.target.parentNode).hasClass('renew')) {
      $('membership_type').value = 'renew';
      if (this.el.getElement('.message')) {
        this.el.getElement('.message').fade('in');
      }
    } else {
      $('membership_type').value = 'gift';
      if (this.el.getElement('.message')) {
        this.el.getElement('.message').fade('out');
      }
    }
    return false;
  }

});

MoMA.MembershipCategories = new Class({

  initialize: function(el) {
    el.getElements('.category').each(function(category) {
      var slide = new Fx.Slide(category.getElement('.benefits'));
      slide.hide();
      category.getElement('.expand').addEvent('click', function() {
        slide.toggle();
        return false;
      });
      category.getElement('.collapse').addEvent('click', function() {
        slide.toggle();
        return false;
      });
    });
  }
});

MoMA.ExpandableContent = new Class({

  Implements: Events,

  initialize: function(el) {
    this.el = el;
    var content = el.getElement('.content');
    el.store('controller', this);
    content.removeClass('hidden');
    var slide = new Fx.Slide(content, {
      resetHeight: true,
      onComplete: function() {
        if (this.slide.open) {
          this.fireEvent('expanded');
        } else {
          this.fireEvent('collapsed');
        }
      }.bind(this)
    });
    content.getParent().addClass('slider');
    if (!el.hasClass('expanded')) {
      slide.hide();
    }
    this.slide = slide;
    el.getElements('.expand').addEvent('click', function() {
      if (slide.open) {
        this.fireEvent('collapse');
      } else {
        this.fireEvent('expand');
      }
      slide.toggle();
      return false;
    }.bind(this));
    el.getElements('.collapse').addEvent('click', function() {
      if (slide.open) {
        this.fireEvent('collapse');
      } else {
        this.fireEvent('expand');
      }
      slide.toggle();
      return false;
    });
    this.addEvent('expand', function() {
      this.el.addClass('expanded');
    }.bind(this));
    this.addEvent('collapsed', function() {
      this.el.removeClass('expanded');
    }.bind(this));
  }

});

MoMA.TabbedContent = new Class({

  Implements: [Events],

  initialize: function(el, page) {
    this.page = page;
    this.el = el;
    page.tabbedContent = this;
    el.store('controller', this);
    el.getElements('.tabs a').addClass('selected');
    el.getElements('.pane').addClass('selected');
    el.getElements('.tabs a').each(function(link) {
      link.addEvent('click', this.onClick.bind(this));
    }.bind(this));
    if (window.location.hash && window.location.hash !== '') {
      this.select(this.getHashId());
    } else {
      this.select(this.getTabId(el.getElement('.tabs a')));
    }
    this.checkURL.periodical(100, this);
    this.minHeight = el.getElement('.tabs').getSize().y;
    this.checkHeight();
    /*if (el.hasClass('horizontal')) {
      var tabHeight = el.getElement('.tabs').getSize().y;
      var holder = el.getElement('.holder');
      holder.setStyle('background-position', '0 ' + (tabHeight - 1) + 'px');
    }*/
  },

  checkURL: function() {
    var hashId = this.getHashId();
    if (hashId && this.currentId != hashId) {
      this.select(hashId);
    }
  },

  onClick: function(event) {
    var target = $(event.target);
    if (target.nodeName.toLowerCase() != 'a') {
      target = target.getParent('a');
    }
    this.select(this.getTabId(target));
  },

  select: function(id) {
    if (!this.el.getElement('.pane.' + id) || !this.el.getElement('.tabs a.' + id) || id == this.currentId) {
      return;
    }
    this.currentId = id;
    this.el.getElements('a.selected').removeClass('selected');
    this.el.getElements('.pane.selected').removeClass('selected');
    this.el.getElements('a.' + id).addClass('selected');
    this.el.getElements('.pane.' + id).addClass('selected');
    this.checkHeight();
    window.location = '#' + id;
    this.fireEvent('onSelect', id);


  },

  checkHeight: function() {
    var pane = this.el.getElement('.pane.selected');
    if (pane && pane.getSize().y < this.minHeight) {
      pane.setStyle('height', this.minHeight - 28);
    }
  },

  getTabId: function(el) {
    return el.get('href').match(/#(.+)/)[1];
  },

  getHashId: function() {
    if (!window.location.hash || window.location.hash === '') {
      return;
    }
    var hashId = window.location.hash;
    if (hashId.substr(0, 1) == '#') {
      hashId = hashId.substr(1);
    }
    return hashId;
  }

});


MoMA.fadeIt = new Class({

   initialize: function(el) {
        this.el = el;
        el.fade('hide');
        el.removeClass('hidden');
        $$('#fadeIt_open')[0].addEvent('click', this.toggle.bind(this));
        $$('#fadeIt_close')[0].addEvent('click', this.toggle.bind(this));

   },

   toggle: function() {
       this.el.fade('toggle');
   }

});

MoMA.Ticker = new Class({

  period: 4500,

  initialize: function(el) {
    this.el = el;
    if (!el.getElement('.selected')) {
      el.getElement('li').addClass('selected');
    }
    this.interval = setInterval(this.rotate.bind(this), this.period);
  },

  rotate: function() {
    var curr = this.el.getElement('.selected');
    if (!curr) {
      return;
    }
    var next = curr.getNext('li');
    if (!next) {
      next = this.el.getElement('li');
    }
    curr.fade('out').retrieve('tween').chain(function() {
      curr.removeClass('selected');
      next.fade('hide');
      next.addClass('selected');
      next.fade('in');
    });
  }

});

MoMA.MediaPlayer = new Class({

  //autoPlay: 'true',
  playerId: 'media-player',
  width: 384,
  height: 288,
  version: 2,

  initialize: function(el, page) {
    this.el = el;
    this.page = page;
    page.player = this;
    window.player = this;
    this.configURL = el.getElement('a.asset').get('href');
    if (el.getElement('a.mp4')) {
      this.mpegURL = el.getElement('a.mp4').get('href');
    }
    this.element = el;
    this.setupShare();
    this.playerTarget = this.element.getElement('.swiff');
    if (window.location.search.contains('noflash')) {
      return;
    }
    try {
      this.showPlayer();
    } catch (e) {
      // IE 7 is throwing an error in the Swiff call, even with try / catch
    }
  },

  showPlayer: function() {
    var embed = $('embed').value;
    embed = embed.replace(/width="\d+"/, 'width="384"');
    embed = embed.replace(/height="\d+"/, 'height="288"');
    if (location.host && location.host != 'www.moma.org') {
      embed = embed.replace(/www.moma.org/, location.host);
    }
    embed = embed.replace(/src="([^"]+)"/, 'src="$1?size=full"');
    this.playerTarget.set('html', embed);
  },

  onComplete: function() {
    // dbug.log('MediaPlayer.onComplete');
    this.page.playlist.playNextItem();
  },

  onError: function(error) {
    dbug.log(error);
  },

  isReady: $empty,
  onPause: $empty,
  onResume: $empty,
  onPlay: $empty,
  onFullscreen: $empty,
  onVolumeChange: $empty,
  play: $empty,

  setupShare: function() {
    var form = this.element.getElement('.share');
    if (!form) {
      return;
    }
    form.addEvent('submit', function() {
      return false;
    });
    form.getElements('a').each(function(link) {
      link.addEvent('click', function() {
        form.getElement('a.selected').removeClass('selected');
        form.getElement('input.selected').removeClass('selected');
        $(link.get('rel')).addClass('selected');
        link.addClass('selected');
        if (link.get('rel') == 'embed') {
          $('embed-toggle').addClass('enabled');
        } else {
          $('embed-toggle').removeClass('enabled');
        }
        return false;
      }.bind(this));
    }.bind(this));

    if ($('embed-toggle')) {
      $('embed-toggle').addEvent('click', function() {
        if ($('embed-toggle').getElement('input').checked) {
          $('embed').value = $('embed').get('data-embed');
        } else {
          $('embed').value = $('embed').get('data-iframe');
        }
      });
    }

    if ($('permalink')) {
      $('permalink').addEvent('click', function() {
        setTimeout(function() {
          $('permalink').select();
        }, 0);
      });
    }

    if ($('embed')) {
      $('embed').addEvent('click', function() {
        setTimeout(function() {
          $('embed').select();
        }, 0);
        return false;
      });
    }
  },

  checkHTML5Video: function() {
    return !!document.createElement('video').canPlayType;
  }

});


MoMA.MediaPlayerLarge = new Class({

  Extends: MoMA.MediaPlayer,

  showPlayer: function() {
    this.playerTarget.set('html', '');
    if (Browser.Plugins.Flash && Browser.Plugins.Flash.version > 8) {
      var player = '/flash/media_player_v' + this.version + '.swf';
      var vars = {
        configUrl: this.configURL
      };
      if (this.version == 1) {
        player = '/flash/media_player.swf';
        vars = {
          assetURL: this.el.getElement('a.asset').get('href'),
          imageURL: this.el.getElement('a.image').get('href')
        }
      }
      this.swiff = new Swiff(player, {
        id: this.playerId,
        width: this.width,
        height: this.height,
        container: this.playerTarget,
        params: {
          wMode: 'opaque',
          allowFullScreen: 'true',
          allowScriptAccess: 'always'
        },
        vars: vars
      });
    } else if (this.mpegURL && this.checkHTML5Video()) {
      var template = '<video id="video" src="{mpegURL}" width="{width}" height="{height}" controls></video>';
      this.playerTarget.set('html', template.substitute(this));
    } else {
      this.playerTarget.set('html', 'Sorry, your browser does not support this video.');
    }
  },

  onPlay: function() {
    this.page.playlist.showPlaying(this.configURL);
  }

});


MoMA.MediaPlayerMed = new Class({

  Extends: MoMA.MediaPlayer,

  showPlayer: function() {
    this.playerTarget.set('html', '');
    if (Browser.Plugins.Flash && Browser.Plugins.Flash.version > 8) {
      var player = '/flash/media_player_v' + this.version + '.swf';
      var vars = {
        configUrl: this.configURL
      };
      if (this.version == 1) {
        player = '/flash/media_player.swf';
        vars = {
          assetURL: this.el.getElement('a.asset').get('href'),
          imageURL: this.el.getElement('a.image').get('href')
        }
      }
      this.swiff = new Swiff(player, {
        id: this.playerId,
        width: this.width,
        height: this.height,
        container: this.playerTarget,
        params: {
          wMode: 'opaque',
          allowFullScreen: 'true',
          allowScriptAccess: 'always'
        },
        vars: vars
      });
    } else if (this.mpegURL && this.checkHTML5Video()) {
      var template = '<video id="video" src="{mpegURL}" width="{width}" height="{height}" controls></video>';
      this.playerTarget.set('html', template.substitute(this));
    } else {
      this.playerTarget.set('html', 'Sorry, your browser does not support this video.');
    }
  },

  playerId: 'media-player-medium'
  //autoPlay: 'false'

});


MoMA.MediaPlayerSmall = new Class({

  Extends: MoMA.MediaPlayer,

  //autoPlay: 'false',
  width: 205,
  height: 163,

  initialize: function(el, page) {
    if ($(document.body).hasClass('modern-women')) {
      this.width = 194;
      this.height = 146;
    }
    if (!MoMA.smallMediaPlayerCount) {
      MoMA.smallMediaPlayerCount = 1;
    } else {
      MoMA.smallMediaPlayerCount++;
    }
    el.store('player', this);
    this.playerId = 'media-player-small' + MoMA.smallMediaPlayerCount;
    this.originalImage = el.getElement('.image').get('href');
    this.parent(el, page);
  },

  showPlayer: function() {
    this.playerTarget.set('html', '');
    if (Browser.Plugins.Flash && Browser.Plugins.Flash.version > 8) {
      var player = '/flash/media_player_v' + this.version + '.swf';
      var vars = {
        configUrl: this.configURL
      };
      if (this.version == 1) {
        player = '/flash/media_player.swf';
        vars = {
          assetURL: this.el.getElement('a.asset').get('href'),
          imageURL: this.el.getElement('a.image').get('href')
        }
      }
      this.swiff = new Swiff(player, {
        id: this.playerId,
        width: this.width,
        height: this.height,
        container: this.playerTarget,
        params: {
          wMode: 'opaque',
          allowFullScreen: 'true',
          allowScriptAccess: 'always'
        },
        vars: vars
      });
    } else if (this.mpegURL && this.checkHTML5Video()) {
      var template = '<video id="video" src="{mpegURL}" width="{width}" height="{height}" controls></video>';
      this.playerTarget.set('html', template.substitute(this));
    } else {
      this.playerTarget.set('html', 'Sorry, your browser does not support this video.');
    }
  }

});


MoMA.MediaPlaylistSmall = new Class({

  initialize: function(el, page) {
    this.el = el;
    this.page = page;
    this.player = this.el.getParent('.JS_Widget').getElement('.JS_MediaPlayerSmall').retrieve('player');
    page.playlist = this;
    this.setupArrows();

  },

  setupArrows: function() {
    var arrows = this.el.getParent('.JS_Widget').getElements('.arrows a');
    if (arrows.length < 2) {
      return;
    }
    if (this.el.getElements('li').length < 2) {
      this.el.getParent('.JS_Widget').getElement('.arrows').setStyle('display', 'none');
      return;
    }
    arrows[0].addEvent('click', this.playPreviousItem.bind(this));
    arrows[1].addEvent('click', this.playNextItem.bind(this));
  },

  playPreviousItem: function() {
    var selected = this.el.getElement('.selected');
    var previous = selected.getPrevious('li');
    if (!previous) {
      previous = this.el.getElements('li').getLast();
    }
    selected.removeClass('selected');
    this.playItem(previous);
    return false;
  },

  playNextItem: function() {
    var selected = this.el.getElement('.selected');
    var next = selected.getNext('li');
    if (!next) {
      next = this.el.getElement('li');
    }
    selected.removeClass('selected');
    this.playItem(next);
    return false;
  },

  playItem: function(item) {
    item.addClass('selected');
    var asset = item.getElement('.asset');
    var mp4 = item.getElement('.mp4');
    var assetTitle = asset.get('html');
    this.player.configURL = asset.get('href');
    if (mp4) {
      this.player.mpegURL = mp4.get('href');
    }
    var title = this.el.getParent('.JS_Widget').getElement('.info .title');
    if (title) {
      title.set('html', assetTitle);
    }
    this.player.showPlayer();
  }

});


MoMA.MediaPlaylist = new Class({

  initialize: function(el, page) {
    this.page = page;
    this.element = el;
    page.playlist = this;
    this.setupTabs();
    this.setupItems();
    this.selectPlaying();
  },

  setupTabs: function() {
    if (this.element.getElements('.playlist-tabs a').length === 0) {
      $('playlist').addClass('hide');
      return;
    }
    this.element.getElements('.playlist-tabs a').each(function(link) {
      link.addEvent('click', function(e) {
        e = new Event(e);
        return this.selectTab($(e.target).get('rel'));
      }.bind(this));
    }.bind(this));
    var first = this.element.getElements('.playlist-tabs a')[0];
    this.setScrollerHeight(first.get('rel'));
  },

  setupItems: function() {
    var items = this.element.getElements('a.media');
    items.each(function(link) {
      link.addEvent('click', function(e) {
        return this.playItem(link);
      }.bind(this));
      var status = new Element('span', {
        'class': 'status',
        'text': 'PLAYING'
      });
      status.inject(link);
    }.bind(this));
  },

  playItem: function(link) {
    if (link.get('href').contains('/interactives/')) {
      return true;
    }
    this.element.getElements('.playing').removeClass('playing');
    link.addClass('playing');
    try {
      var assetURL = link.get('rel');
      if (assetURL.contains(',')) {
        var assetParts = assetURL.split(',');
        this.page.player.configURL = assetParts[0];
        this.page.player.mpegURL = assetParts[1];
        this.page.player.showPlayer();
      } else {
        this.page.player.configURL = assetURL;
        this.page.player.showPlayer();
      }
      this.updatePlayerInfo(link);
    } catch(e) {
      dbug.log(e.message);
    }
    return false;
  },

  updatePlayerInfo: function(link) {
    var info = window.player.element.getElement('.info');
    info.set('html', '<div class="player-loading">Loading...</div>');
    var request = new Request({
      method: 'get',
      url: link.get('href').replace('/explore/multimedia', '/explore/multimedia/info'),
      onComplete: function(response) {
        info.set('html', response);
        window.player.setupShare();
      }
    });
    request.send();
  },

  playNextItem: function() {
    var curr = this.element.getElement('.playing');
    curr.removeClass('playing');
    if (curr) {
      var next = curr.getNext('a.media');
      if (next) {
        this.playItem(next);
      }
    }
  },

  selectTab: function(id) {
    if (!$(id)) {
      return false;
    }
    this.element.getElements('div.selected').removeClass('selected');
    $(id).addClass('selected');
    var selectedSearch = $$('.playlist-tabs .selected');
    if (selectedSearch.length > 0) {
      selectedSearch[0].removeClass('selected');
    }
    var tabSearch = $$(".playlist-tabs a[rel='" + id + "']");
    if (tabSearch.length > 0) {
      tabSearch[0].addClass('selected');
    }
    this.setScrollerHeight(id);
    return false;
  },

  setScrollerHeight: function(id) {
    var height = $(id).getSize().y;
    var title = $(id).getElement('h3');
    var lang = $(id).getElement('form');
    if (title) {
      height -= title.getSize().y + 6;
    }
    if (lang) {
      height -= lang.getSize().y;
    }
    if ($(id).getElement('.scrollable')) {
      $(id).getElement('.scrollable').setStyle('height', height);
    }
  },

  selectPlaying: function(url) {
    var assetURL = false;
    if (!url) {
      var asset = $$('#player .content a.asset');
      if (asset.length > 0) {
        assetURL = asset[0].get('href');
      }
    } else {
      assetURL = url;
    }
    if (assetURL) {
      var item = this.element.getElement('a[rel=' + assetURL + ']');
      if (item) {
        item.addClass('playing');
      }
    }
  }

});

MoMA.MediaPlaylistMed = new Class({

  Extends: MoMA.MediaPlaylist,

  initialize: function(el, page) {
    this.parent(el, page);
    this.setupPageControls();
    this.shortenTitles();
  },

  setupPageControls: function() {
    this.currPage = 0;
    var prev = this.element.getElement('.controls .prev');
    var next = this.element.getElement('.controls .next');
    prev.addEvent('click', this.prevPage.bind(this));
    next.addEvent('click', this.nextPage.bind(this));
    this.element.getElement('.slider').set('tween', {
      duration: 350
    });
    if (this.element.getElements('.selected ol').length > 2) {
      //dbug.log(this.element.getElements('.selected ol'));
      this.element.getElement('.controls').addClass('show');
    }
  },

  shortenTitles: function() {
    var revertRelated;
    if ($('tab-related')) {
      revertRelated = $('tab-related').expose();
    }
    this.element.getElements('.info h4').each(function(h4) {
      if (h4.getParent('#tab-related')) {
        h4.shorten(60);
      } else {
        h4.shorten(65);
      }
    });
    if ($('tab-related')) {
      revertRelated();
    }
  },

  prevPage: function(e) {
    e = new Event(e);
    var link = $(e.target);
    if (link.hasClass('disabled')) {
      return false;
    }
    this.element.getElement('.controls .next').removeClass('disabled');
    this.currPage--;
    var lists = this.element.getElements('ol');
    if (this.currPage === 0) {
      link.addClass('disabled');
    }
    this.updatePageView();
    return false;
  },

  nextPage: function(e) {
    e = new Event(e);
    var link = $(e.target);
    if (link.hasClass('disabled')) {
      return false;
    }
    this.element.getElement('.controls .prev').removeClass('disabled');
    this.currPage++;
    var lists = this.element.getElements('ol');
    if (this.currPage == lists.length - 2) {
      link.addClass('disabled');
    }
    this.updatePageView();
    return false;
  },

  updatePageView: function() {
    var slider = this.element.getElement('.slider');
    var lists = this.element.getElements('ol');
    var list = lists[this.currPage];
    slider.tween('left', -(list.getPosition(slider).x + 1));
  },

  updatePlayerInfo: function() {
    var download = '';
    var title = this.element.getElement('a.playing .info h4').get('html');
    var link = this.element.getElement('a.playing');
    if (link.get('rel').contains('.mp3')) {
      var url = link.get('rel').match(/\/audio_file.+\.mp3/)[0];
      download = '&nbsp;&nbsp;<a href="' + url + '"><small>Download</small></a>';
    }
    $('player-medium').getElement('.info p').set('html', title + download);
  }

});

MoMA.MediaPlaylistCollection = new Class({

  Extends: MoMA.MediaPlaylistMed,

  shortenTitles: function() {
    var revertVideos, revertInteractives;
    if ($('tab-videos')) {
      revertVideos = $('tab-videos').expose();
    }
    if ($('tab-interactives')) {
      revertInteractives = $('tab-interactives').expose();
    }
    this.element.getElements('.info h4').each(function(h4) {
      if (h4.getParent('#tab-related')) {
        h4.shorten(60);
      } else {
        h4.shorten(65);
      }
    });
    if ($('tab-videos')) {
      revertVideos();
    }
    if ($('tab-interactives')) {
      revertInteractives();
    }
  }

});

MoMA.MediaChannels = new Class({

  initialize: function(el, page) {
    this.element = el;
    this.currGroup = 'group-0';
    this.setupItems();
    this.setupBack();
    this.page = page;
    page.channels = this;
    page.addEvent('onInitialize', this.clickSelected.bind(this));
  },

  clickSelected: function() {
    var selected = this.element.getElement('a.selected');
    if (!selected.hasClass('featured') && !selected.hasClass('most-recent')) {
      this.element.getElement('.back').removeClass('disabled');
      var list = selected.getParent('ol');
      list.addClass('selected');
      this.currGroup = list.get('id');
    }
    this.clickItem(selected, true);
  },

  setupItems: function() {
    this.element.getElements('.holder a').each(function(link) {
      link.addEvent('click', function() {
        this.clickItem(link);
        return false;
      }.bind(this));
    }.bind(this));
    this.element.getElement('.slider').set('tween', {
      duration: 275,
      onComplete: this.finishLoading.bind(this)
    });
  },

  clickItem: function(link, initialClick) {
    var slider = this.element.getElement('.slider');
    this.selectItem(link);
    this.page.packages.showLoadingMessage();
    if (link.get('rel') && $(link.get('rel'))) {
      var group = $(link.get('rel'));
      this.currGroup = link.get('rel');
      group.addClass('selected');
      this.linkClicked = link;
      this.isNewContext = true;
      if (initialClick === true) {
        slider.setStyle('left', -(group.getPosition(slider).x));
        this.finishLoading();
      } else {
        slider.tween('left', -(group.getPosition(slider).x));
      }
    } else {
      this.linkClicked = link;
      this.finishLoading();
      if (initialClick === true) {
        slider.setStyle('left', -(link.getPosition(slider).x));
      }
    }
  },

  selectItem: function(link) {
    var list = link.getParent('ol');
    list.getElements('a.selected').removeClass('selected');
    list.getElements('ol.selected').removeClass('selected');
    link.addClass('selected');
  },

  finishLoading: function() {

    if (!this.linkClicked) {
      return;
    }
    var link = this.linkClicked;
    this.linkClicked = false;

    if (link.hasClass('featured')) {
      this.element.getElement('.title').set('text', 'Select');
    } else {
      this.element.getElement('.title').set('text', link.get('text'));
    }

    if (this.isNewContext) {
      this.isNewContext = false;
      if (link.hasClass('featured')) {
        this.updatePackages(link);
      } else {
        this.clickItem($(this.currGroup).getElement('a'));
        this.element.getElement('.back').removeClass('disabled');
      }
    } else {
      this.updatePackages(link);
    }
  },

  updatePackages: function(link) {
    this.page.packages.setBreadCrumbs(link);
    var href = link.get('href').match(/#(.+)$/);
    if (href && href.length === 2) {
      this.page.packages.showChannel(href[1]);
    }
  },

  reset: function() {
    this.clickItem(this.element.getElement('.featured'));
  },

  setupBack: function() {
    var back = this.element.getElement('.back');
    var slider = this.element.getElement('.slider');
    back.addEvent('click', function() {
      var left = parseInt(slider.getStyle('left'), 10);
      if (left === 0) {
        return false;
      }
      this.isNewContext = true;
      slider.tween('left', left + 243).retrieve('tween').chain(function() {
        $(this.currGroup).removeClass('selected');
        this.currGroup = $(this.currGroup).getParent('ol').get('id');
        $(this.currGroup).getElement('.selected').removeClass('selected');
        //dbug.log('Clicking ' + $(this.currGroup).getElement('a').get('text'));
        this.clickItem($(this.currGroup).getElement('a'));
        if (this.currGroup == 'group-0') {
          this.element.getElement('.back').addClass('disabled');
        }
      }.bind(this));
      return false;
    }.bind(this));
  },

  getGroupLink: function(rel) {
    //dbug.log(rel);
    return this.element.getElement("a[rel='" + rel + "']");
  }

});

MoMA.MediaPackages = new Class({

  initialize: function(el, page) {
    this.page = page;
    this.element = el;
    page.packages = this;
    this.setupPageControls();
  },

  setupPageControls: function() {
    var prev = this.element.getElement('.controls .prev');
    var next = this.element.getElement('.controls .next');
    prev.addEvent('click', this.prevPage.bind(this));
    next.addEvent('click', this.nextPage.bind(this));
    this.element.getElement('.slider').set('tween', {
      duration: 350
    });
    this.element.getElement('.breadcrumbs a').addEvent('click', function() {
      return false;
    });
  },

  prevPage: function(e) {
    e = new Event(e);
    var link = $(e.target);
    if (link.hasClass('disabled')) {
      return false;
    }
    this.element.getElement('.controls .next').removeClass('disabled');
    this.currPage--;
    var lists = this.element.getElements('.selected ol');
    if (this.currPage === 0) {
      link.addClass('disabled');
    }
    this.updatePageView();
    return false;
  },

  nextPage: function(e) {
    e = new Event(e);
    var link = $(e.target);
    if (link.hasClass('disabled')) {
      return false;
    }
    this.element.getElement('.controls .prev').removeClass('disabled');
    this.currPage++;
    var lists = this.element.getElements('.selected ol');
    if (this.currPage == lists.length - 3) {
      link.addClass('disabled');
    }
    this.updatePageView();
    return false;
  },

  updatePageView: function() {
    var slider = this.element.getElement('.slider');
    var lists = this.element.getElements('.selected ol');
    var list = lists[this.currPage];
    slider.tween('left', -(list.getPosition(slider).x + 1));
  },

  showPageControls: function() {
    this.element.getElement('.controls').addClass('show');
  },

  hidePageControls: function() {
    this.element.getElement('.controls').removeClass('show');
  },

  setBreadCrumbs: function(link) {
    //dbug.log('setBreadCrumbs', link);
    var crumbs = this.element.getElement('.breadcrumbs');
    crumbs.removeClass('loading');
    crumbs.set('html', '');
    if (link && !link.hasClass('featured')) {
      //dbug.log(0);
      if (!link.hasClass('default')) {
        //dbug.log(1);
        this.addBreadCrumb(link);
      }
      while (link.getParent('ol')) {
        //dbug.log(2);
        var list = link.getParent('ol');
        //dbug.log(list);
        if (list.get('id') == 'group-0') {
          //dbug.log(2.1);
          break;
        }
        if (!link.hasClass('default')) {
          var separator = new Element('span', {
            html: '&nbsp;&gt;&nbsp;'
          });
          separator.inject(crumbs, 'top');
        }
        //dbug.log(2.2);
        link = this.page.channels.getGroupLink(list.get('id'));
        //dbug.log(link);
        this.addBreadCrumb(link);
      }
      var finalSeparator = new Element('span', {
        html: '&nbsp;&gt;&nbsp;'
      });
      finalSeparator.inject(crumbs, 'top');
    }
    var topLevel = new Element('a', {
      href: '#',
      html: 'Multimedia',
      events: {
        click: function() {
          this.page.channels.reset();
          return false;
        }.bind(this)
      }
    });
    topLevel.inject(crumbs, 'top');
  },

  showChannel: function(id) {
    if ($(id)) {
      this.setupChannel(id);
    } else {
      this.loadChannel(id);
    }
  },

  loadChannel: function(id) {
    this.loadingChannel = id;
    var request = new Request({
      url: '/explore/multimedia/channel/' + id,
      method: 'get',
      onComplete: function(html) {
        var slider = this.element.getElement('.slider');
        var existing = slider.get('html');
        slider.set('html', existing + html);
        this.setupChannel(id);
        this.setupChannelControls(id);
      }.bind(this)
    });
    request.send();
  },

  setupChannelControls: function(id) {
    var target = $(id);
    var slider = this.element.getElement('.slider');
    var width = 0;
    var lists = target.getElements('ol');
    this.currPage = 0;
    this.element.getElement('.slider').setStyle('left', 0);
    lists.each(function(list) {
      width += list.getSize().x;
    });
    slider.setStyle('width', width);
    if (lists.length > 3) {
      this.showPageControls();
    } else {
      this.hidePageControls();
    }
    target.getElements('.package').each(function(link) {
      link.getElement('h4').shorten(60);
    }.bind(this));
  },

  setupChannel: function(id) {
    if (!id && this.loadingChannel) {
      id = this.loadingChannel;
      this.loadingChannel = false;
    }
    var holder = this.element.getElement('.holder');
    holder.getElement('.slider').setStyle('opacity', 1.0);
    holder.removeClass('loading');
    this.element.getElement('.controls .prev').addClass('disabled');
    this.element.getElement('.controls .next').removeClass('disabled');
    this.element.getElements('.selected').removeClass('selected');
    $(id).addClass('selected');
  },

  showLoadingMessage: function() {
    var holder = this.element.getElement('.holder');
    holder.getElement('.slider').setStyle('opacity', 0.5);
    holder.addClass('loading');
  },

  addBreadCrumb: function(link) {
    var crumbs = this.element.getElement('.breadcrumbs');
    var crumb = new Element('a', {
      href: '#',
      text: link.get('text'),
      rel: link.get('rel'),
      events: {
        click: function(e) {
          e = new Event(e);
          var rel = $(e.target).get('rel');
          var channels = this.page.channels;
          var link = channels.getGroupLink(rel);
          channels.clickItem(link);
          return false;
        }.bind(this)
      }
    }).inject(crumbs, 'top');
  }

});

MoMA.SearchForm = new Class({

  initialize: function(el) {
    this.el = el;
    this.input = el.getElement('.input');
    this.button = el.getElement('.button');
    this.container = el.getElement('.container');
    this.setup();
  },

  setup: function() {
    this.input.addEvent('focus', this.focus.bind(this));
    this.input.addEvent('blur', this.blur.bind(this));
    this.button.addEvent('mouseenter', function() {
      this.button.addClass('button-hover');
    }.bind(this));
    this.button.addEvent('mouseleave', function() {
      this.button.removeClass('button-hover');
    }.bind(this));
  },

  focus: function() {
    if (this.container) {
      this.container.addClass('focus');
    } else {
      this.input.addClass('focus');
    }
    if (this.input.hasClass('clear-on-focus')) {
      this.input.removeClass('clear-on-focus');
      this.input.value = '';
    }
  },

  blur: function() {
    if (this.input.value === '') {
      if (this.container) {
        this.container.removeClass('focus');
      } else {
        this.input.removeClass('focus');
      }
    }
  }

});

MoMA.ImageCaption = new Class({

  initialize: function(el, page) {
    this.el = el;
    this.page = page;
    this.isSetup = false;
    if ($('no-image-captions')) {
      return;
    }
    this.setup();
    if (el.getParent('.JS_TabbedContent')) {
      this.setupTabBehavior();
    }
    if (el.getParent('.JS_CourseListing')) {
      this.setupCourseBehavior();
    }
  },

  setup: function() {
    if (!this.imageIsLoaded(this.el)) {
      this.el.addEvent('load', this.setup.bind(this));
      return;
    }
    this.setupDelay = 0;
    if (this.el.getParent('.JS_TabbedContent') &&
        !this.el.getParent('.pane').hasClass('selected')) {
      return;
    }
    if (this.el.getParent('.JS_CourseListing') &&
        !this.el.getParent('.course.expanded') &&
        !this.el.getParent('.subpane.selected')) {
      return;
    }
    if (!this.isSetup) {
      this.el.measure(function() {
        this.size = this.el.getSize();
        this.isSetup = true;
        this.context = this.setupContext();
        this.trigger = this.setupTrigger();
        this.caption = this.setupCaption();
        this.setupEvents();
      }.bind(this));
    }
  },

  setupContext: function() {
    var size = this.size;
    var className = this.el.className;
    className = className.replace('JS_ImageCaption', '');
    var context = new Element('div', {
      'class': 'image-caption-context ' + className,
      styles: {
        position: 'relative',
        top: 0,
        width: size.x,
        height: size.y,
        background: 'transparent url(' + this.el.get('src') + ') no-repeat',
        'background-size': this.size.x + 'px ' + this.size.y + 'px',
        margin: this.el.getStyle('margin')
      }
    });
    this.el.setStyle('display', 'none');
    this.el.store('image-caption', context);
    context.inject(this.el, 'after');
    context.store('image', this.el);
    if (this.el.getParent('.text-right')) {
      context.setStyle('float', 'right');
      var br = new Element('br', {
        'class': 'clear'
      });
      br.inject(context, 'after');
    }
    return context;
  },

  setupTrigger: function() {
    var className = 'image-caption';
    className += this.el.hasClass('flickr') ? ' flickr-caption' : '';
    className += this.el.hasClass('top-caption') ? ' top-caption' : '';
    var trigger = new Element('a', {
      href: '#',
      'class': className,
      text: this.el.hasClass('flickr') ? 'FLICKR' : 'i'
    });
    trigger.inject(this.context);
    this.addBackground(trigger);
    return trigger;
  },

  setupCaption: function() {
    var caption = new Element('div', {
      html: this.el.get('longdesc'),
      'class': 'image-caption'
    });
    this.context.measure(function() {
      var size = this.context.getSize();
      caption.setStyles({
        'max-width': size.x - 26
      });
      if (this.el.hasClass('top-caption')) {
        caption.addClass('top-caption');
      }
      caption.inject(this.context);
      var coordinates = caption.getCoordinates(this.context);
      var captionSize = caption.getSize();
      var top = coordinates.top + coordinates.height - 28;
      if (this.el.hasClass('bottom-caption')) {
        top -= (captionSize.y - 28);
      } else if (captionSize.y > 30) {
        top += 17;
      }
      caption.setStyles({
        top: top,
        bottom: 'auto'
      });
      var background = this.addBackground(caption);
      background.addClass('hidden');
      caption.addClass('hidden');
      caption.setStyle('visibility', 'visible');
    }.bind(this));
    return caption;
  },

  setupEvents: function() {
    this.trigger.addEvent('mouseover', function() {
      this.caption.removeClass('hidden');
      this.caption.retrieve('background').removeClass('hidden');
      this.trigger.addClass('hidden');
      this.trigger.retrieve('background').addClass('hidden');
      $(document.body).addClass('image-caption-hovered');
      if (this.el.hasClass('top-caption')) {
        $(document.body).addClass('top-caption-hovered');
      }
      this.context.addClass('image-caption-context-hovered');
      // Webkit render bug
      //this.repaint($('main'));
    }.bind(this));
    this.caption.addEvent('mouseleave', function() {
      this.caption.addClass('hidden');
      this.caption.retrieve('background').addClass('hidden');
      this.trigger.removeClass('hidden');
      this.trigger.retrieve('background').removeClass('hidden');
      $(document.body).removeClass('image-caption-hovered');
      this.context.removeClass('image-caption-context-hovered');
      // Webkit render bug
    }.bind(this));
  },

  addBackground: function(target) {
    var background = new Element('div', {
      'class': 'image-caption-bg'
    });
    target.measure(function() {
      var coordinates = target.getCoordinates(this.context);
      var size = this.getSize(target);
      var top = coordinates.top;
      background.setStyles({
        top: top - 1,
        left: coordinates.left + coordinates.width - size.x - 1,
        width: size.x,
        height: size.y,
        'font-size': 9
      });
      target.store('background', background);
    }.bind(this));
    return background.inject(this.context);
  },

  // From sajithmr.com
  imageIsLoaded: function(img) {
    if (img.getSize().x > 0 && img.getSize().y > 0) {
      return true;
    }
    if (!img.complete) {
      return false;
    }
    if (typeof img.naturalWidth != "undefined" &&
        img.naturalWidth === 0) {
      return false;
    }
    return true;
  },

  setupTabBehavior: function() {
    var tabs = this.el.getParent('.JS_TabbedContent').retrieve('controller');
    tabs.addEvent('onSelect', function() {
      if (!this.isSetup) {
        this.setup();
      }
    }.bind(this));
  },

  setupCourseBehavior: function() {
    this.page.addEvent('onCourseExpanded', function() {
      if (!this.isSetup) {
        this.setup();
      }
    }.bind(this));
  },

  getSize: function(el) {
    var size = {
      x: null,
      y: null
    };
    if (el.getSize().x === 0 || el.getSize().y === 0) {
      var clone = el.clone();
      clone.setStyle('visibility', 'hidden');
      clone.inject(document.body);
      size = clone.getSize();
      clone.destroy();
    } else {
      size = el.getSize();
    }
    return size;
  },

  repaint: function(el) {
    el.addClass('repaint');
    el.removeClass('repaint');
  }

});

MoMA.Expander = new Class({

  initialize: function(el) {
    this.el = el;
    var target = $(el.get('rel'));
    if (!target) {
      return;
    }
    if (el.hasClass('disable-animation')) {
      this.animate = false;
      this.target = target;
      target.addClass('hidden');
    } else {
      this.animate = true;
      target.addClass('hidden');
      target.setStyles({
        position: 'absolute',
        visibility: 'hidden'
      });
      target.removeClass('hidden');
      target.setStyle('height', target.getSize().y);
      target.setStyles({
        position: 'static',
        visibility: 'visible'
      });
      this.slide = new Fx.Slide(target).hide();
    }
    el.addEvent('click', this.toggle.bind(this));
    var collapse = target.getElement('.collapse');
    if (collapse) {
      collapse.addEvent('click', this.toggle.bind(this));
    }
  },

  toggle: function() {
    if (this.animate) {
      this.el.toggleClass('expanded');
      this.slide.toggle();
    } else {
      this.target.toggleClass('hidden');
      this.el.toggleClass('hidden');
    }
    return false;
  }

});


MoMA.VisitorInformation = new Class({

  initialize: function(el) {
    el.selectedIndex = 0;
    el.addEvent('change', function() {
      window.location = el.options[el.selectedIndex].value;
    });
  }

});

MoMA.ENewsSignup = new Class({

  initialize: function(el) {
    var defaultValue = true;
    if ($('e-news')) {
      $('e-news').addEvent('focus', function() {
        if (defaultValue) {
          $('e-news').value = '';
          defaultValue = false;
        }
        $('e-news').setStyle('color', '#000');
      });
    }
  }

});

MoMA.HomeCalendar = new Class({

  initialize: function(el) {
    this.el = el;
    this.position = 0;
    this.pageSize = el.getElement('li').getSize().x;
    this.maxPosition = this.pageSize * (el.getElements('li').length - 1);

    if (el.getElements('li').length < 2) {
      this.el.getElement('.nav').addClass('hidden');
    }

    el.getElements('li h3').each(function(title) {
      title.shorten(35);
    });

    this.slider = el.getElement('ol');
    this.prevButton = el.getElement('.prev');
    this.nextButton = el.getElement('.next');
    this.slider.set('tween', {
      duration: 500,
      transition: Fx.Transitions.Quart.easeOut
    });
    this.prevButton.addEvent('click', this.prev.bind(this));
    this.nextButton.addEvent('click', this.next.bind(this));
  },

  prev: function() {
    if (!this.prevButton.hasClass('disabled')) {
      this.position += this.pageSize;
      this.slider.tween('left', this.position);
      this.nextButton.removeClass('disabled');
      if (this.position >= 0) {
        //this.slider.setStyle('left', 0);
        this.prevButton.addClass('disabled');
      }
    }
    return false;
  },

  next: function() {
    if (!this.nextButton.hasClass('disabled')) {
      this.position -= this.pageSize;
      this.slider.tween('left', this.position);
      this.prevButton.removeClass('disabled');
      if (this.position <= -this.maxPosition) {
        //this.slider.setStyle('left', -this.maxPosition);
        this.nextButton.addClass('disabled');
      }
    }
    return false;
  }

});

MoMA.HomeNews = new Class({

  initialize: function(el) {

  }

});

MoMA.UserLogin = new Class({

  initialize: function(el) {
    el.addEvent('click', function() {
      Console.openToRegister();
      return false;
    });
  }

});

MoMA.SendToPhone = new Class({

  initialize: function(el) {
    el.addEvent('click', function() {
      if ($(document.body).hasClass('ss-phone-enabled')) {
        var request = new Request.JSON({
          url: '/social/shiftspace/server/?method=sms.send',
          data: $H({
            msg: el.get('rel'),
            toself: 1
          }).toQueryString(),
          onComplete: function(json) {
            alert('The event details have been sent to your mobile phone.');
          }
        });
        request.send();
      } else {
        alert('To send this event to your phone you must first register and validate your phone number.');
        //Console.openToRegister();
      }
      return false;
    });
  }

});

MoMA.Share = new Class({

  shareActive: false,

  initialize: function() {
    $$('.share').each(function(relative) {
      relative.addEvent('mouseover', function() {
        this.show(relative);
      }.bind(this));
      relative.addEvent('mouseout', function() {
        this.hide(relative);
      }.bind(this));
    }.bind(this));
    $('share-options').getElements('.services a').each(function(link) {
      link.addEvent('click', function(e) {
        new Event(e).stop();
        if (link.hasClass('pinterest')) {
          Asset.javascript('//assets.pinterest.com/js/pinmarklet.js');
        } else {
          var width = link.get('data-width') || 520;
          var height = link.get('data-height') || 430;
          var popup = window.open(link.get('href'), 'share', 'height=' + height + ',width=' + width);
          if (window.focus) {
            popup.focus();
          }
        }
      });
    });
  },

  setup: function(url, title) {
    if (!url) {
      url = location.href;
    }
    if (!title) {
      title = document.title;
    }
    url = url.replace(location.hostname, 'www.moma.org');
    title = title.replace('MoMA | ', '');
    $('share-options').getElements('.services a').each(function(link) {
      var template = link.get('data-url');
      if (template) {
        link.set('href', template.substitute({
          url: encodeURIComponent(url),
          title: encodeURIComponent(title)
        }));
      }
    }.bind(this));
    var emailSubject = encodeURIComponent('MoMA.org: ' + title);
    var emailBody = encodeURIComponent(url);
    $('share-options').getElement('a.email').set('href', 'mailto:?subject=' + emailSubject + '&body=' + emailBody);
  },

  show: function(relative) {
    if (relative.get('id') == 'share-page') {
      $('user-dropdown').addClass('gray');
    }
    var url = relative.get('data-url');
    var title = relative.get('data-title');
    if (url && url != '' &&
        title && title != '') {
      this.setup(url, title);
    } else {
      var url = relative.getParents('.course').getElement('.view-detail').get('href');
      var title = relative.getParents('.course').getElement('h3').get('text');
      if (url.length && title.length) {
        this.shareActive = true;
        this.setup(window.location.href.split('#')[0].replace(window.location.host, 'moma.org') + url[0], title[0]);
        $('share-options').addClass('hover');
        $('share-page').addClass('hover');
      } else if (!this.shareActive) {
        this.setup();
      }
    }
    relative.addClass('hover');
  },

  hide: function(relative) {
    if (relative.get('id') == 'share-page') {
      $('user-dropdown').removeClass('gray');
    }
    relative.removeClass('hover');
  }

});

MoMA.SharePage = new Class({

  Implements: [Events],

  initialize: function(el, page) {
    if (!$('share-page')) {
      return;
    }
    this.el = el;
    this.page = page;
    page.share = this;
  },

  loadOptions: function() {
    new Request.HTML({
      url: '/users/share_page',
      update: $('share-options'),
      onComplete: this.ready.bind(this)
    }).get();
  },

  ready: function(response) {
    $('share-options').removeClass('loading');
    $('share-options').setStyle('display', 'block');
    $('share-page').addEvent('mouseenter', function() {
      if (!this.visible) {
        this.positionShareWidget($('share-page'));
        $('share-options').addClass('share-page');
        $('user-dropdown').addClass('gray');
        this.show(true);
      }
    }.bind(this));
    $('share-page').addEvent('mouseleave', function(e) {
      var related = $(e.relatedTarget);
      if (related && (related.get('id') == 'share-options' || related.getParent('#share-options'))) {
        $('share-page').addClass('hover');
        $('user-dropdown').addClass('gray');
      } else if (!$('share-options').hasClass('email')) {
        this.hide();
      }
    }.bind(this));
    $('share-options').addEvent('mouseleave', function(e) {
      var related = $(e.relatedTarget);
      if (related && (related.get('id') == 'share-page' || related.getParent('#share-page')) ||
          $('share-options').hasClass('email')) {
        return;
      }
      if ($('share-options').hasClass('share-page')) {
        this.hide();
      }
    }.bind(this));
    $$('a.share').addEvent('click', this.toggle.bind(this));
    $('share-options').getElement('.close').addEvent('click', function(e) {
      new Event(e).stop();
      this.toggle(e);
      $('share-options').removeClass('email');
      $('share-menu').setStyle('display', 'block');
      $('share-menu').fade('show');
      $('share-email').setStyle('display', 'none');
      $('share-send-done').setStyle('display', 'none');
      $('share-options').setStyle('height', 124);
    }.bind(this));
    $('share-options').set('tween', {
      duration: 'short'
    });
    $(document.body).addEvent('click', function(e) {
      var e = new Event(e);
      if (this.ignoreClicks) {
        return true;
      }
      if ($(e.target).getParent('#share-options')) {
        return true;
      }
      this.hide(e);
    }.bind(this));
    var widget = $('share-options');
    var resetWidget = widget.expose();
    widget.store('size', widget.getSize());
    resetWidget();

    $('share-options').getElement('a.email').addEvent('click', function(e) {
      new Event(e).stop();
      if (!$(document.body).hasClass('logged-in')) {
        if (confirm('Sorry, sharing by e-mail requires that you log in first. Would you like to log in now?')) {
          window.location = '/login';
        }
      } else {
        $('share-menu').fade('out');
        $('share-options').tween('height', 275).get('tween').chain(function() {
          $('share-menu').setStyle('display', 'none');
          $('share-email').setStyles({
            display: 'block',
            opacity: 0
          });
          $('share-options').addClass('email');
          $('share-email').fade('in');
        });
      }
    });

    $('share-options').getElements('.text.default').each(function(input) {
      input.store('default', input.value);
      input.addEvent('focus', function() {
        if (input.hasClass('default')) {
          input.value = '';
          input.removeClass('default');
        }
      });
      input.addEvent('blur', function() {
        if (input.value == '') {
          input.value = input.retrieve('default');
          input.addClass('default');
        }
      });
    });

    $('share-options').getElements('input.date').addEvent('focus', this.showDatePicker.bind(this));
    $('share-options').getElements('a.date').addEvent('click', function(e) {
      new Event(e).stop();
      if (!$('share-date-picker').hasClass('visible')) {
        this.showDatePicker(e);
      } else {
        this.hideDatePicker();
      }
    }.bind(this));

    $('share-email').addEvent('submit', this.emailSubmit.bind(this));

    this.show();

  },

  toggle: function(e) {
    e = new Event(e);
    var target = $(e.target);
    if (!target.hasClass('share') && target.get('id') != 'share-page') {
      target = target.getParent('.share');
      if (target && target.get('rel')) {
        $('share-options').addClass('limited');
        var title = target.get('title').replace('Share: ', '');
        this.setup(title, target.get('rel'));
      } else {
        $('share-options').removeClass('limited');
        this.setup();
      }
    }
    if (target) {
      this.target = target;
      this.positionShareWidget(target);
    } else if (this.visible) {
      this.hide();
      return false;
    } else {
      return false;
    }
    if (this.visible) {
      this.hide();
    } else {
      this.show();
    }
    return false;
  },

  show: function(setup) {
    if ($('share-options').hasClass('loading')) {
      this.loadOptions();
      return;
    }
    if (setup && !this.pageSetup) {
      this.pageSetup = true;
      this.setup();
    }
    $('share-options').setStyles({
      display: 'block',
      opacity: 0
    });
    if ($('share-options').hasClass('share-page')) {
      $('share-options').fade('show');
    } else {
      $('share-options').fade('in');
    }
    this.visible = true;
  },

  hide: function() {
    this.visible = false;
    if (!$('share-options').hasClass('share-page')) {
      $('share-options').fade('out').retrieve('tween').chain(function() {
        $('share-options').removeClass('email');
        $('share-options').removeClass('sms');
        $('share-options').setStyle('height', $('share-options').retrieve('size').y - 6);
        $('share-menu').fade('show');
        $('share-menu').setStyle('display', 'block');
        $('share-email').fade('hide');
        $('share-email').setStyle('display', 'none');
        $('share-options').setStyle('display', 'none');
      });
    } else {
      $('share-options').setStyle('display', 'none');
    }
    $('share-page').removeClass('hover');
    $('share-options').removeClass('share-page');
    $('user-dropdown').removeClass('gray');
  },

  setup: function(title, url) {
    if (title && url) {
      this.title = title;
      this.url = url;
    } else {
      var title, meta = $$('meta[name=stitle]');
      if (meta.length > 0) {
        title = meta[0].get('content');
      }
      if (!title) {
        title = document.title;
      }
      this.title = title.replace("MoMA | ", "");
      this.url = window.location.href.replace(window.location.host, 'www.moma.org');
    }
    this.setupLinks();
    this.setupEmail();
    //this.setupText();
  },

  positionShareWidget: function(target) {
    if (target.getParent().hasClass('wide')) {
      target = target.getParent();
    }
    var widget = $('share-options');
    var widgetSize = widget.retrieve('size');
    var position = 'bottomRight';
    var edge = 'topRight';
    if (target.getPosition().y - window.getScroll().y > window.getSize().y - (widgetSize.y + 20)) {
      // Over target
      position = 'topRight';
      edge = 'bottomRight';
    }
    if (target.getParent('.SSContentView')) {
      widget.inject(target.getParent('.SSContentView'));
    } else {
      widget.inject(document.body);
    }
    widget.position({
      relativeTo: target,
      position: position,
      edge: edge
    });
  },

  setupLinks: function() {
    this.setupTwitter();
    this.setupDelicious();
    this.setupFacebook();
    this.setupGoogle();
    this.shortenURL();
  },

  setupEmail: function() {
    $('email-subject').value = 'MoMA.org: ' + this.title;
    $('email-message').value = 'More information can be found at: ' + this.url;
    if (typeof MoMAUser == 'object' && MoMAUser.isLoggedIn()) {
      $('email-message').value = MoMAUser.getUsername() + ' has sent you this page. '  + $('email-message').value;
    }
  },

  setupText: function() {
    $('share-sms').getElement('.title').set('html', this.title);
    this.setSMSMessage();
  },

  setSMSMessage: function() {
    if (typeof MoMAUser == 'object' && MoMAUser.isLoggedIn()) {
      var url = this.url;
      if (this.shortened && this.shortened[url]) {
        url = this.shortened[url];
      }
      $('sms-message').value = MoMAUser.getUsername() + ' has sent you: ' + this.title + ' from MoMA.org. More info at: ' + url;
    }
  },

  bookmarkItem: function() {
    dbug.log('Bookmark');
    return false;
  },

  shareItem: function() {
    dbug.log('Share');
    return false;
  },

  setupTwitter: function() {
    var link = $('share-options').getElement('.twitter');
    this.shortURL = this.url;
    if (this.shortened && this.shortened[this.url]) {
      this.shortURL = this.shortened[this.url];
    }
    var statusTemplate = "{title} at MoMA.org {shortURL}";
    var status = this.template(statusTemplate);
    status = this.encode(status);
    link.set('href', 'http://twitter.com/home/?status=' + status);
  },

  setupDelicious: function() {
    var link = $('share-options').getElement('.delicious');
    var urlTemplate = "http://delicious.com/save?jump=yes&url={url}&title={title}";
    var url = this.template(urlTemplate, true);
    link.set('href', url);
  },

  setupFacebook: function() {
    var link = $('share-options').getElement('.facebook');
    var urlTemplate = "http://www.facebook.com/sharer.php?u={url}&t={title}";
    var url = this.template(urlTemplate, true);
    link.set('href', url);
    link.addEvent('click', function(e) {
      new Event(e).stop();
      if (typeof facebook != 'undefined' && facebook.connected) {
        var data = {
          url: this.url,
          title: this.title
        };
        var meta = $$('meta[name=image]');
        if (meta.length > 0 && meta[0].get('content')) {
          data.images = facebook.getImageSet(meta[0].get('content'));
        }
        facebook.publish(data);
      } else {
        window.open(url, 'sharer', 'toolbar=0,status=0,width=626,height=436');
      }
      this.hide();
    }.bind(this));
  },

  setupGoogle: function() {
    var link = $('share-options').getElement('.google');
    var urlTemplate = "http://www.google.com/bookmarks/mark?op=edit&bkmk={url}&title={title}";
    var url = this.template(urlTemplate, true);
    link.set('href', url);
  },

  setupDigg: function() {
    var link = $('share-options').getElement('.digg');
    var urlTemplate = "http://digg.com/remote-submit?phase=2&url={url}&title={title}";
    var url = this.template(urlTemplate, true);
    link.set('href', url);
  },

  setupStumbleUpon: function() {
    var link = $('share-options').getElement('.stumbleupon');
    var urlTemplate = "http://www.stumbleupon.com/submit?url={url}&title={title}";
    var url = this.template(urlTemplate, true);
    link.set('href', url);
  },

  emailSubmit: function(e) {
    new Event(e).stop();
    if (this.hasValue('email-to', "You must enter at least one e-mail address to send to.") &&
        this.validateEmail('email-to', "One of the e-mail addresses you wish to send to is invalid.") &&
        //this.hasValue('email-from', "You must enter your e-mail address to send from.") &&
        //this.validateEmail('email-from', "The e-mail address you wish to send from is invalid.") &&
        //this.validateDate('email-date', "Sorry the date you entered is invalid.") &&
        this.hasValue('email-subject', "Oops, you need to enter a subject.") &&
        this.hasValue('email-message', "Oops, you need to enter a message.")
        //this.hasValue('email-message', "Oops, you don't seem to be sharing this page.")
        ) {
      new Request({
        url: '/form_mailer/share_page',
        onComplete: function() {
          $('share-email').fade('out').retrieve('tween').chain(function() {
            $('share-email').fade('out');
            $('share-options').tween('height', 100).retrieve('tween').chain(function() {
              $('share-email').setStyle('display', 'none');
              $('share-send-done').setStyles({
                display: 'block',
                opacity: 0
              });
              $('share-send-done').fade('in');
            });
          }.bind(this));
        }
      }).post({
        to: $('email-to').value,
        //from: $('email-from').value,
        subject: $('email-subject').value,
        body: $('email-message').value
      });
    }
  },

  smsSubmit: function(e) {
    new Event(e).stop();
    if (this.hasValue('sms-to', "You must enter at least one phone number to send to.") &&
        this.validatePhone('sms-to', "One of the phone numbers you wish to send to is invalid.") &&
        this.validateDate('sms-date', "Sorry the date you entered is invalid.") &&
        this.hasValue('sms-message', "Oops, you need to enter a message.") &&
        this.validateMessage('sms-message', "Oops, you don't seem to be sharing this page.")) {
      $('share-sms').fade('out').retrieve('tween').chain(function() {
        $('share-sms').setStyle('display', 'none');
        $('share-captcha').setStyles({
          display: 'block',
          opacity: 0
        });
        $('share-captcha').fade('in');
        $('share-options').tween('height', $('share-send').getSize().y + $('share-title').getSize().y + 10);
        this.captchaTarget = 'sms';
      }.bind(this));
    }
  },

  captchaSubmit: function(e) {
    new Event(e).stop();
    this.hide();
    var message = '';
    if (this.captchaTarget == 'email') {
      message = 'Your e-mail ';
      var dateInput = 'email-date';
    } else {
      message = 'Your text message ';
      var dateInput = 'sms-date';
    }
    var now = new Date();
    if ($(dateInput).value == now.format('%b %d, %Y')) {
      message += 'will be sent shortly.';
    } else {
      message += 'is now scheduled.';
    }
    /*Console.notimoo.show({
      message: message
    });*/
  },

  hasValue: function(target, message) {
    if ($(target).value == '' || $(target).value == $(target).retrieve('default')) {
      this.showValidationAlert(message);
      return false;
    }
    return true;
  },

  validateEmail: function(target, message) {
    var valid = true;
    var emails = $(target).value.split(',');
    for (var i = 0; i < emails.length; i++) {
      var test = (emails[i].match(/^\s*\w+@\w+\.\w+\s*/) == null) ? false : true;
      valid = valid && test;
    }
    if (!valid) {
      this.showValidationAlert(message);
    }
    return valid;
  },

  validatePhone: function(target, message) {
    var valid = true;
    var phones = $(target).value.split(',');
    for (var i = 0; i < phones.length; i++) {
      var test = (phones[i].replace(/[^0-9]/g, '').match(/^1?[0-9]{10}$/) ? true : false);
      valid = valid && test;
    }
    if (!valid) {
      this.showValidationAlert(message);
    }
    return valid;
  },

  validateDate: function(target, message) {
    var now = Date.parse('today');
    try {
      var test = Date.parse($(target).value);
    } catch(e) {}
    if ($type(test) != 'date' || test.getTime() === NaN || test.getTime() < now.getTime()) {
      this.showValidationAlert(message);
      return false;
    }
    return true;
  },

  validateMessage: function(target, message) {
    if ($(target).value.contains(this.url)) {
      return true;
    }
    if (this.shortened && this.shortened[this.url] &&
        $(target).value.contains(this.shortened[this.url])) {
      return true;
    }
    this.showValidationAlert(message);
    return false;
  },

  showValidationAlert: function(message) {
    this.ignoreClicks = true;
    alert(message);
    /*Console.showModal(message, {
      button1: {
        label: "OK",
        callback: function() {
          setTimeout(function() {
            this.ignoreClicks = false;
          }.bind(this), 0);
        }.bind(this)
      }
    });*/
  },

  shortenURL: function() {
    if (this.shortened && this.shortened[this.url]) {
      return this.shortened[this.url];
    } else if (!this.shortened) {
      this.shortened = {};
    }
    var request = new Request.JSONP({
      url: window.location.protocol + '//api.bit.ly/shorten',
      data: {
        longUrl: this.url,
        login: 'momashare',
        apiKey: 'R_727da7802f4145c7d9f5ba5287e5ce5f',
        version: '2.0.1',
        format: 'json'
      },
      onComplete: function(response) {
        var longURL = this.url;
        if (response.results && response.results[longURL]) {
          this.shortened[longURL] = response.results[longURL].shortUrl;
          this.setupTwitter();
          this.setSMSMessage();
        }
      }.bind(this)
    });
    request.send();
  },

  encode: function(value) {
    return encodeURIComponent(value);
  },

  template: function(template, encode) {
    return template.substitute({
      title: encode ? this.encode(this.title) : this.title,
      url: encode ? this.encode(this.url) : this.url,
      shortURL: encode ? this.encode(this.shortURL) : this.shortURL
    });
  },

  showDatePicker: function(e) {
    var target = $(e.target);
    if (target.tagName.toLowerCase() != 'input') {
      target = target.getParent('form').getElement('input.date');
    }
    var position = target.getPosition($('share-send'));
    $('share-date-picker').setStyles({
      left: position.x,
      top: position.y + 60
    });
    $('share-date-picker').store('target', target);

    $('share-options').addEvent('click', function(e) {
      e = new Event(e);
      if ($('share-date-picker').hasClass('visible')) {
        if (e.target.get('id') != 'share-date-picker' &&
            !e.target.getParent('#share-date-picker') &&
            e.target.get('id') != $('share-date-picker').retrieve('target').get('id')) {
          $('share-date-picker').removeClass('visible');
        }
      }
    });

    $('share-date-picker').addClass('visible');
    if ($('share-date-picker').getElement('.loading')) {
      var now = new Date();
      new Request({
        url: now.format('/visit/calendar/date_picker/%Y/%m/%d'),
        method: 'get',
        onComplete: function(html) {
          $('share-date-picker').set('html', html);
          this.setupDatePicker();
        }.bind(this)
      }).send();
    }
  },

  setupDatePicker: function() {
    $('share-date-picker').getElements('.month-nav a').addEvent('click', function(e) {
      new Event(e).stop();
      var target = $(e.target);
      if (target.tagName.toLowerCase() != 'a') {
        target = target.getParent('a');
      }
      $('share-date-picker').set('html', '<div class="loading">Loading...</div>');
      new Request({
        url: target.get('href').replace(/\/calendar\/(\d\d\d\d)/, "/calendar/date_picker/$1"),
        method: 'get',
        onComplete: function(html) {
          $('share-date-picker').set('html', html);
          this.setupDatePicker();
        }.bind(this)
      }).send();
    }.bind(this));
    $('share-date-picker').getElements('table a').addEvent('click', function(e) {
      new Event(e).stop();
      var target = $(e.target);
      if (target.tagName.toLowerCase() != 'a') {
        target = target.getParent('a');
      }
      var linkDate = target.get('href').match(/(\d{4})\/(\d+)\/(\d+)/);
      if (linkDate.length == 4) {
        var date = new Date();
        date.setYear(parseInt(linkDate[1]));
        date.setMonth(parseInt(linkDate[2]) - 1);
        date.setDate(parseInt(linkDate[3]));
      }
      var target = $('share-date-picker').retrieve('target');
      target.value = date.format('%b ') + date.format('%d').replace(/0(\d)/, '$1') + ', ' + date.format('%Y');
      this.hideDatePicker();
    }.bind(this));
  },

  hideDatePicker: function() {
    $('share-date-picker').removeClass('visible');
  }

});

function shareToggle(x, y) {
  MoMA.share.toggle({
    x: x,
    y: y
  });
}

MoMA.CalendarDateRange = new Class({

  Implements: Events,

  initialize: function(el) {
    this.el = el;
    this.date = $('date');
    this.start = $('startdate');
    this.end = $('enddate');
    this.setupValues();
    this.setupClasses();
    this.setupDateEvents();
    this.setupRangeEvents();
    this.setupButtons();
    this.setupPickers();
  },

  setupValues: function() {
    if (this.date && (this.date.value === '' || this.date.value == 'Enter date')) {
      this.date.value = 'Enter date';
      this.date.store('defaultValue', 'Enter date');
    }
    if (this.start && (this.start.value === '' || this.start.value == 'Start date')) {
      this.start.value = 'Start date';
      this.start.store('defaultValue', 'Start date');
    }
    if (this.end && (this.end.value === '' || this.end.value == 'End date')) {
      this.end.value = 'End date';
      this.end.store('defaultValue', 'End date');
    }
  },

  setupClasses: function() {
    if (this.date.value != 'Enter date') {
      this.date.removeClass('default');
    }
    if (this.start && this.start.value != 'Start date') {
      this.start.removeClass('default');
    }
    if (this.end && this.end.value != 'End date') {
      this.end.removeClass('default');
    }
  },


  setupDateEvents: function(){
    if (this.date) {
      this.date.addEvent('focus', this.focusInput.bind(this));
      this.el.addEvent('submit', this.submit.bind(this));
      this.date.addEvent('click', function() { return false; });
      document.body.addEvent('click', function(e) {
        if (!$(e.target).getParent('.picker')) {
          this.hidePicker();
        }
      }.bind(this));
    }
  },

  setupRangeEvents: function() {
    if (this.start && this.end) {
      this.start.addEvent('focus', this.focusInput.bind(this));
      this.end.addEvent('focus', this.focusInput.bind(this));
      this.start.addEvent('click', function() { return false; });
      this.end.addEvent('click', function() { return false; });
      document.body.addEvent('click', function(e) {
        if (!$(e.target).getParent('.picker')) {
          this.hidePicker();
        }
      }.bind(this));
    }
  },

  setupButtons: function() {
    this.el.getElements('.picker-button').each(function(button) {
      button.addEvent('click', function() {
        var pickerId = button.get('rel');
        if ($(pickerId).hasClass('hidden')) {
          this.showPicker(pickerId);
        } else {
          this.hidePicker(pickerId);
        }
        return false;
      }.bind(this));
    }.bind(this));
  },

  setupPickers: function() {
    this.el.getElements('.picker').each(function(picker) {
      var id = picker.get('id').match(/(.+)-picker/)[1];
      var coords = $(id).getCoordinates($('page'));
      picker.setStyles({
        left: coords.left - 1
        //top: coords.top + coords.height - 11
      });
      this.setupPicker(picker);
    }.bind(this));
  },

  setupPicker: function(picker) {
    var day, month, year;
    var months = ['Blank', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    var id = picker.get('id').match(/(.+)-picker/)[1];
    if (picker.getParent('#search-day')) {
      picker.getElements('td a').each(function(link) {
        var href = link.get('href');
        var urlRegex = /(\d+)\/(\d+)\/(\d+)/;
        if (href.indexOf('?') != -1) {
          day = parseInt(href.match(/day=(\d+)/)[1], 10);
          month = parseInt(href.match(/month=(\d+)/)[1], 10);
          year = parseInt(href.match(/year=(\d+)/)[1], 10);
        } else if (href.match(urlRegex)) {
          var date = href.match(urlRegex);
          year = parseInt(date[1], 10);
          month = parseInt(date[2], 10);
          day = parseInt(date[3], 10);
        }
        if (month < 10) {
          month = '0' + month;
        }
        if (day < 10) {
          day = '0' + day;
        }
        link.set('href', '/visit/calendar/' + year + '/' + month + '/' + day);
        this.fireEvent('formatDatePickerLink', link);
      }.bind(this));
    } else {
      picker.getElements('td a').each(function(link) {
        link.addEvent('click', function(e) {
          new Event(e).stop();
          var href = link.get('href');
          var urlRegex = /(\d+)\/(\d+)\/(\d+)/;
          if (href.indexOf('?') != -1) {
            day = parseInt(href.match(/day=(\d+)/)[1], 10);
            month = parseInt(href.match(/month=(\d+)/)[1], 10);
            year = parseInt(href.match(/year=(\d+)/)[1], 10);
          } else if (href.match(urlRegex)) {
            var date = href.match(urlRegex);
            year = parseInt(date[1], 10);
            month = parseInt(date[2], 10);
            day = parseInt(date[3], 10);
          }
          $(id).value = months[month] + ' ' + day + ', ' + year;
          $(id).removeClass('default');
          this.hidePicker(id + '-picker');
          this.fireEvent('dateChosen', [year, month, day]);
        }.bind(this));
        this.fireEvent('formatDatePickerLink', link);
      }.bind(this));
    }
    picker.getElements('.month-nav a').each(function(link) {
      link.addEvent('click', function(e) {
        new Event(e).stop();
        var request = new Request({
          url: link.get('href').replace('/calendar/', '/calendar/date_picker/'),
          method: 'get',
          onComplete: function(html) {
            $(id + '-picker').set('html', html);
            this.setupPicker($(id + '-picker'));
          }.bind(this)
        });
        request.send();
      }.bind(this));
    }.bind(this));
  },

  focusInput: function(e) {
    e = new Event(e);
    var inputName = $(e.target).get('name');
    this.showPicker(inputName + '-picker');
    if ($(e.target).hasClass('default')) {
      $(e.target).removeClass('default');
      $(e.target).value = '';
    }
  },

  showPicker: function(id) {
    $(id).removeClass('hidden');
    this.fireEvent('showPicker');
    if (this.openPicker) {
      this.hidePicker(this.openPicker);
    }
    this.openPicker = id;
  },

  hidePicker: function(id) {
    if ($type(id) != 'string' && $type(this.openPicker) == 'string') {
      id = this.openPicker;
    }
    if ($(id)) {
      $(id).addClass('hidden');
    }
    this.openPicker = false;
  },

  submit: function() {
    if (this.date && this.date.value == 'Enter date') {
      this.date.value = '';
    }
    if (this.start && this.start.value == 'Start date') {
      this.start.value = '';
    }
    if (this.end && this.end.value == 'End date') {
      this.end.value = '';
    }
    /*
    if (this.date.value === '' && this.start.value === '' && this.end.value ||
        this.start.value !== '' && this.end.value === '' ||
        this.end.value !== '' && this.start.value === '') {
      this.setupValues();
      this.setupClasses();
      return false;
    }
    */
  }

});

MoMA.TicketsCalendarPicker = new Class({

  Extends: MoMA.CalendarDateRange,

  initialize: function(el, page) {
    this.addEvent('formatDatePickerLink', function(link) {
      var today = new Date().format('%Y-%m-%d');
      if (link.get('data-date') < today) {
        link.addClass('past');
        var span = new Element('span', {
          'class': link.className,
          html: link.get('html')
        }).inject(link.getParent());
        link.destroy();
      }
    });
    this.parent(el, page);
    $('today').addEvent('change', this.loadTickets.bind(this));
    $('tomorrow').addEvent('change', this.loadTickets.bind(this));
    $('date').addEvent('change', function() {
      var date = Date.parse($('date').value);
      if (this.isValidDate(date)) {
        $('date').removeClass('invalid-date');
        $('entered_date').set('data-date', date.getFullYear() + '-' + this.zeroize(date.getMonth() + 1) + '-' + this.zeroize(date.getDate()));
        this.loadTickets();
      } else {
        $('date').addClass('invalid-date');
      }
    }.bind(this));
    this.addEvent('dateChosen', function(year, month, day) {
      $('date').removeClass('invalid-date');
      $('entered_date').set('data-date', year + '-' + this.zeroize(month) + '-' + this.zeroize(day));
      this.loadTickets();
    }.bind(this));
    this.addEvent('showPicker', this.onShowPicker.bind(this));
    this.setupSubmitButtons();
    this.setupJoinPromos();
    $('entered_date').addEvent('change', function() {
      this.showPicker('date-picker');
    }.bind(this));
  },

  setupSubmitButtons: function() {
    var form = this.el.getParent('form');
    form.getElements('.button-rounded').each(function(submit) {
      submit.addEvent('click', function() {
        this.submitClicked = true;
      }.bind(this));
    }.bind(this));
  },

  handleSubmit: function(e) {
    if (!this.submitClicked) {
      new Event(e).stop();
      this.loadTickets();
    }
  },

  loadTickets: function() {
    this.el.getParent('form').set('action', '/visit/calendar/tickets/{year}/{month}/{day}'.substitute({
      year: this.getYear(),
      month: this.getMonth(),
      day: this.getDay()
    }));
    $('ajax_content').set('html', '<div class="box no-bottom-border"><div class="box-gray-white"><p class="top gray-type"><strong>LOADING</strong></p></div></div>');
    new Request({
      url: '/visit/calendar/tickets/ajax/{year}/{month}/{day}'.substitute({
        year: this.getYear(),
        month: this.getMonth(),
        day: this.getDay()
      }),
      onComplete: function(html) {
        $('ajax_content').set('html', html);
        this.setupSubmitButtons();
        this.setupJoinPromos();
      }.bind(this)
    }).post();
  },

  setupJoinPromos: function() {
    this.setupJoinPromoSelect('ADULT');
    this.setupJoinPromoSelect('SNCTZ');
  },

  setupJoinPromoSelect: function(id) {
    if ($(id)) {
      var select = $(id).getElement('select');
      if (select) {
        select.addEvent('change', function() {
          if (select.options[select.selectedIndex].value.toInt() > 2) {
            $('member_message_' + id).removeClass('hidden');
          } else {
            $('member_message_' + id).addClass('hidden');
          }
        });
      }
    }
  },

  onShowPicker: function() {
    $('entered_date').checked = true;
  },

  getYear: function() {
    var date = this.getDate();
    return date.getFullYear();
  },

  getMonth: function() {
    var date = this.getDate();
    return date.getMonth() + 1;
  },

  getDay: function() {
    var date = this.getDate();
    return date.getDate();
  },

  getDate: function() {
    if ($('today').checked) {
      return Date.parse($('today').get('data-date'));
    } else if ($('tomorrow').checked) {
      return Date.parse($('tomorrow').get('data-date'));
    } else {
      var date = Date.parse($('entered_date').get('data-date'));
      if (this.isValidDate(date)) {
        return date;
      } else {
        $('date').addClass('invalid-date');
      }
    }
  },

  isValidDate: function(date) {
    return ($type(date.getFullYear()) == 'number');
  },

  zeroize: function(num) {
    num = num.toInt();
    if (num < 10) {
      return '0' + num;
    } else {
      return num;
    }
  }

});

MoMA.Widget = new Class({

  initialize: function(el, page) {
    this.el = el;
    this.page = page;
    el.store('widget', this);
    var href = this.getHref();
    if (href) {
      this.load(href);
    }
  },

  load: function(href) {
    this.request = new Request({
      method: 'get',
      url: href,
      onComplete: this.inject.bind(this)
    }).send();
  },

  getHref: function() {
    var link = this.el.getElement('a');
    if (!link) {
      return false;
    } else {
      var href = link.get('href');
      if (link.get('rel')) {
        if (href.indexOf('?') == -1) {
          href += '?' + link.get('rel');
        } else {
          href += '&' + link.get('rel');
        }
      }
      return href;
    }
  },

  inject: function(html) {
    this.el.set('html', html);
    this.page.initializeControllers(this.el);
  }

});


MoMA.WidgetLink = new Class({

  initialize: function(el) {
    el.addEvent('click', function(e) {
      var widgetId = el.get('rel');
      if ($(widgetId) && $(widgetId).retrieve('widget')) {
        var href = el.get('href') + '?widget_id=' + widgetId;
        $(widgetId).retrieve('widget').load(href);
        return false;
      }
    });
  }

});


MoMA.ExhibitionImages = new Class({

  initialize: function(el) {
    el.getElements('a').each(function(link) {
      link.addEvent('click', function() {
        $('placeholder').set('src', link.get('href'));
        $('placeholder').set('alt', link.get('alt'));
        $('desc').set('html', link.get('alt'));
        return false;
      });
    });
  }

});

MoMA.EventImages = new Class({

  initialize: function(el) {
    el.getElements('a').each(function(link) {
      link.addEvent('click', function() {
        $('placeholder-div').set('html', '');
        $('placeholder-div').adopt(
          new Element('img', {
            id: 'placeholder',
            src: link.get('href'),
            alt: link.get('alt'),
            longdesc: link.get('alt'),
            'class': 'JS_ImageCaption'
          })
        );

        new MoMA.ImageCaption($('placeholder'), this);

        return false;
      });
    });
  }

});

MoMA.PreviousExhibitions = new Class({

  initialize: function(el) {
    this.el = el;
    this.dropDown = el.getElement('.drop-down');
    var link = el.getElement('a.previous');
    if (link) {
      link.addEvent('click', function() {
        return false;
      });
    }
    this.setupDropDown();
    el.addEvent('mouseenter', this.showDropDown.bind(this));
    el.addEvent('mouseleave', this.delayedHideDropDown.bind(this));
    this.dropDown.addEvent('mouseenter', this.resetHideDropDown.bind(this));
  },

  setupDropDown: function() {
    var pos = this.el.getPosition($('page'));
    var size = this.el.getSize();
    this.dropDown.setStyles({
      left: pos.x,
      top: pos.y + size.y - 10,
      width: size.x
    });
  },

  showDropDown: function() {
    this.resetHideDropDown();
    this.el.addClass('hover');
  },

  delayedHideDropDown: function() {
    this.resetHideDropDown();
    this.delayed = this.hideDropDown.delay(500, this);
  },

  resetHideDropDown: function() {
    if (this.delayed) {
      $clear(this.delayed);
      this.delayed = false;
    }
  },

  hideDropDown: function() {
    this.el.removeClass('hover');
    this.delayed = false;
  }

});

MoMA.HomeNews = new Class({

  initialize: function(el) {
    this.pages = el.getElements('li');
    this.list = el.getElement('ol');
    this.controls = el.getElement('.pages');
    this.holder = el.getElement('.relative');
    this.list.set('tween', {
      duration: 750,
      transition: Fx.Transitions.Quart.easeOut
    });
    if (this.pages.length > 1) {
      for (var i = 0; i < this.pages.length; i++) {
        this.addPageLink(i);
      }
    }
  },

  addPageLink: function(num) {
    var className = (num === 0) ? 'selected' : '';
    var link = new Element('a', {
      href: '#',
      rel: num,
      'class': className,
      html: '&bull;',
      events: {
        click: this.select.bind(this)
      }
    });
    link.inject(this.controls);
  },

  select: function(e) {
    e = new Event(e);
    var link = $(e.target);
    var num = parseInt(link.get('rel'), 10);
    this.list.tween('left', -642 * num);
    this.controls.getElements('.selected').removeClass('selected');
    link.addClass('selected');
    return false;
  }

});

MoMA.OneTimeSubmit = new Class({

  initialize: function(el) {
    var form = el.getParent('form');

    // Only add the handler once
    if (form.hasClass('JS_OneTimeSubmit')) {
      return;
    }

    el.addEvent('click', function() {
      // We only care about some buttons (not "back to cart" for instance)
      form.addClass('submission');
    });

    form.addClass('JS_OneTimeSubmit');
    form.addEvent('submit', function() {
      if (!form.hasClass('submission')) {
        return true;
      }
      if (form.hasClass('submitted')) {
        return false;
      }
      form.addClass('submitted');
      form.getElements('input').each(function(input) {
        if (input.get('type') == 'image') {
          input.setStyle('cursor', 'default');
          input.setStyle('opacity', 0.5);
        }
      });
    });
  }

});

MoMA.CommentForm = new Class({

  initialize: function(el) {
    this.el = el;
    el.addEvent('submit', this.submit.bind(this));
  },

  submit: function(e) {
    if ($('name').value === '' ||
        $('email').value === '' ||
        $('content').value === '' ||
        $('captcha_input').value === '') {
      this.respond('Please fill in all required fields (name, email, comment, and spam check).');
      new Event(e).stop();
    }
  },

  respond: function(msg) {
    var response = this.el.getElement('.response');
    response.set('html', msg);
    response.removeClass('hidden');
  }

});

MoMA.BlogGallery = new Class({

  initialize: function(el, page) {
    this.page = page;
    window.gallery = this;
    var id = el.get('id');
    if (!window[id]) {
      return;
    }
    this.el = el;
    this.data = window[id].images;
    this.url = window[id].url;
    this.current = 0;
    this.images = [];

    if (location.hash.match(/^#gallery-(\d+)/)) {
      var match = location.hash.match(/^#gallery-(\d+)/);
      this.current = parseInt(match[1], 10) - 1;
    }

    this.buildNavigation();
    this.show();
  },

  show: function() {
    if (this.el.getElement('.current')) {
      var curr = this.el.getElement('.current');
      curr.removeClass('current');
      curr.addClass('hidden');
    }
    if (this.images[this.current]) {
      this.images[this.current].removeClass('hidden');
      this.images[this.current].addClass('current');
    } else {
      var image = this.buildImage(this.current);
      this.images[this.current] = image;
      $(image).addClass('current');
    }

    var nextIndex = (this.current + 1) % this.data.length;
    if (!this.images[nextIndex]) {
      // Preload next image
      this.images[nextIndex] = this.buildImage(nextIndex);
    }

    this.el.setStyle('height', 'auto');
    this.el.setStyle('height', this.el.getSize().y);
    this.updateStatus();
    this.updatePermalink();
  },

  next: function() {
    this.current++;
    if (this.current == this.data.length) {
      this.current = 0;
    }
    this.show();
    return false;
  },

  prev: function() {
    this.current--;
    if (this.current < 0) {
      this.current = this.data.length - 1;
    }
    this.show();
    return false;
  },

  buildNavigation: function() {

    var nav = new Element('div', {
      'class': 'nav'
    });

    var prev = new Element('a', {
      href: '#',
      'class': 'prev',
      text: 'Prev',
      events: {
        click: this.prev.bind(this)
      }
    });
    prev.inject(nav);

    var next = new Element('a', {
      href: '#',
      'class': 'next',
      text: 'Next',
      events: {
        click: this.next.bind(this)
      }
    });
    next.inject(nav);

    this.status = new Element('span', {
      'class': 'status'
    });
    this.status.inject(nav);

    nav.inject(this.el);

    this.permalink = new Element('a', {
      href: this.url,
      text: 'Permalink',
      'class': 'permalink'
    });
    this.permalink.inject(this.el);

    var clear = new Element('br', {
      'class': 'clear'
    });
    clear.inject(this.el);

    this.updateStatus();
  },

  buildImage: function(index) {

    var data = this.data[index];
    var div = new Element('div', {
      'class': 'wp-caption'
    });

    if (index != this.current) {
      div.addClass('hidden');
    }

    var img = new Element('img', {
      src: data.url,
      width: data.width,
      height: data.height
    });
    img.inject(div);

    var caption = new Element('div', {
      'class': 'wp-caption-text'
    });
    caption.inject(div);
    caption.set('html', data.caption.replace('<br>', '<br />'));

    if (data.description && data.description !== "") {
      var description = new Element('div', {
        'class': 'wp-description-text'
      });
      description.inject(div);
      description.set('html', data.description.replace('<br>', '<br />'));
    }

    div.inject(this.el);
    this.page.fireEvent('buildImage', [div]);

    return div;
  },

  updateStatus: function() {
    this.status.set('text', 'Image ' + (this.current + 1) + ' / ' + this.data.length);
  },

  updatePermalink: function() {
    this.permalink.set('href', this.url + '#gallery-' + (this.current + 1));
  }

});

MoMA.BlogWidget = new Class({

  initialize: function(el) {
    this.el = el;
    var list = this.el.getElement('ol');
    var request = new Request.JSON({
      url: '/explore/inside_out/api/get_recent_posts/',
      onSuccess: function(json) {
        json.posts.each(function(post) {
          var item = new Element('li');
          item.set('html', "<a href=\"{url}\">{title}</a>".substitute(post));
          item.inject(list);
        }.bind(this));
      }
    });
    request.get();
  },

  addPost: function(post) {
    //console.log(post);

  }

});

MoMA.RisingCurrentsHeading = new Class({

  initialize: function(el) {
    this.el = el;
    el.getElements('.navigation a').each(function(link) {
      var id = 'rising-currents-' + link.get('rel');
      if (!$(id)) {
        return;
      }
      link.addEvent('click', function() {
        this.choose(id);
      }.bind(this));
      $(id).removeClass('hidden');
      var slide = new Fx.Slide($(id)).hide();
      $(id).store('slide', slide);
      $(id).getElement('.close').addEvent('click', function() {
        this.choose(id);
        return false;
      }.bind(this));
    }.bind(this));
    if (location.hash && location.hash.length > 1) {
      var id = 'rising-currents-' + location.hash.substr(1);
      if ($(id)) {
        this.choose(id);
      }
    }
  },

  choose: function(id) {
    var selected = $$('.dropdown.selected');
    if (selected.length > 0 && id != selected[0].get('id')) {
      selected[0].retrieve('slide').hide();
      selected[0].removeClass('selected');
      this.el.getElement('.navigation .selected').removeClass('selected');
      $(id).retrieve('slide').show();
    } else {
      $(id).retrieve('slide').toggle();
    }
    $(id).toggleClass('selected');
    this.el.getElement('.navigation .' + id.substr(16)).toggleClass('selected');
  }

});

MoMA.PrintStudioHeading = new Class({

  initialize: function(el) {
    this.el = el;
    el.getElements('.navigation a').each(function(link) {
      var id = 'print-studio-' + link.get('rel');
      if (!$(id)) {
        return;
      }
      link.addEvent('click', function(e) {
        this.choose(id);
      }.bind(this));
      $(id).removeClass('hidden');
      var slide = new Fx.Slide($(id)).hide();
      $(id).store('slide', slide);
      $(id).getElement('.close').addEvent('click', function() {
        this.choose(id);
        return false;
      }.bind(this));
    }.bind(this));
    if (location.hash && location.hash.length > 1) {
      var id = 'print-studio-' + location.hash.substr(1);
      if ($(id)) {
        this.choose(id);
      }
    } else if ($('main').hasClass('blog-index')) {
      this.choose('print-studio-about');
    }
  },

  choose: function(id) {
    var selected = $$('.dropdown.selected');
    if (selected.length > 0 && id != selected[0].get('id')) {
      selected[0].retrieve('slide').hide();
      selected[0].removeClass('selected');
      this.el.getElement('.navigation .selected').removeClass('selected');
      $(id).retrieve('slide').show();
    } else {
      $(id).retrieve('slide').toggle();
    }
    $(id).toggleClass('selected');
    this.el.getElement('.navigation .' + id.substr(13)).toggleClass('selected');
  }

});

MoMA.BlogArchiveTags = new Class({

  initialize: function(el) {
    el.getElement('.show-selected').addEvent('click', function() {
      $('all-tags').addClass('hidden');
      $('selected-tags').removeClass('hidden');
      return false;
    });
    el.getElement('.show-all').addEvent('click', function() {
      $('all-tags').removeClass('hidden');
      $('selected-tags').addClass('hidden');
      return false;
    });
  }

});

MoMA.SidebarBlogWidget = new Class({
  initialize: function(el) {
    new Request({
      url: '/widgets/blog_sidebar',
      onComplete: function(html) {
        el.set('html', html);
      }
    }).get();
  }
});

MoMA.HomeBlogLink = new Class({
  initialize: function(el) {
    new Request({
      url: '/widgets/blog_home_link',
      onComplete: function(html) {
        var parent = el.getParent();
        parent.set('html', html);
        var link = parent.getElement('a.gray-type');
        link.set('html', link.get('text'));
        link.shorten(25);
      }
    }).get();
  }
});

MoMA.PromotionBlogWidget = new Class({
  initialize: function(el) {
    new Request({
      url: '/widgets/blog_promotion',
      onComplete: function(html) {
        el.set('html', html);
        var list = el.getElement('ul');
        var items = el.getElements('li');
        while (list.getSize().y > 100) {
          var last = items.pop();
          last.destroy();
        }
      }
    }).get();
  }
});

MoMA.FadeSlides = new Class({
  initialize: function(el) {
    var slideshow = el.getElements('img');
    slideshow.each(function(img) {
      img.set('tween', {
        duration: 1500,
        transition: Fx.Transitions.Quart.easeOut
      });
    });
    var visible = 0;
    var zIndex = 1;
    var slideshowInterval = setInterval(function() {
      var lastImage = slideshow[visible];
      lastImage.fade('out');
      visible++;
      if (visible == slideshow.length) {
        visible = 0;
      }
      var image = slideshow[visible];
      image.fade('hide');
      image.addClass('visible');
      image.setStyle('z-index', ++zIndex);
      image.fade('in');
    }, 8000);
    slideshow[0].addClass('visible');
  }
});

MoMA.HeaderSlides = new Class({

  initialize: function(el) {
    this.el = el;
    this.position = 0;
    this.slides = el.getElements('.slide');
    if (this.slides.length < 2) {
      this.slides[0].addClass('selected');
      return;
    }
    this.setupControls();
    this.slides.each(function(slide, num) {
      if (num === 0) {
        slide.addClass('selected');
        if (!this.el.hasClass('no-resize')) {
          this.resizeHeight(slide);
        }
      } else {
        slide.addClass('hidden');
      }
    }.bind(this));
    this.el.addClass('header-slides-ready');
  },

  resizeHeight: function(slide) {
    if (slide.getSize().y < 20) {
      setTimeout(this.resizeHeight.bind(this, slide), 100);
    } else {
      this.el.setStyle('height', slide.getSize().y);
    }
  },

  setupControls: function() {
    var controls = new Element('div', {
      html: '<a class="prev" href="#">&lt;</a><a class="next" href="#">&gt;</a><br class="clear">',
      'class': 'controls'
    });
    controls.inject(this.el);
    var prev = controls.getElement('.prev');
    var next = controls.getElement('.next');
    prev.addEvent('click', function(e) {
      e = new Event(e).stop();
      this.position--;
      if (this.position < 0) {
        this.position = this.slides.length - 1;
      }
      this.slides[this.position].setStyle('left', -this.el.getSize().x);
      this.update();
    }.bind(this));
    next.addEvent('click', function(e) {
      e = new Event(e).stop();
      this.position++;
      if (this.position == this.slides.length) {
        this.position = 0;
      }
      this.slides[this.position].setStyle('left', this.el.getSize().x);
      this.update();
    }.bind(this));
  },

  update: function() {
    var current = this.el.getElement('.selected');
    current.removeClass('selected');
    var selected = this.slides[this.position];
    selected.removeClass('hidden');
    selected.addClass('selected');
    selected.addClass('moving');
    selected.tween('left', 0).retrieve('tween').chain(function() {
      current.addClass('hidden');
      selected.removeClass('moving');
    });
  }

});

MoMA.CourseListing = new Class({

  initialize: function(el, page) {
    this.page = page;
    this.el = el;
    this.subtabs = [];

    this.setupSubtabs();
    this.setupCourses();
    this.setupCollapseExpandAll();
    if (window.location.hash && window.location.hash !== '') {
      this.justLoaded = true;
      this.selectCourse(this.getHashId());
    }
    this.checkURL.periodical(100, this);
    this.setupPrint();

    if (this.el.hasClass('online')) {
      var checkOnlineTab = function() {
        if ($('online-sponsorship')) {
          if (this.el.hasClass('selected')) {
            $('online-sponsorship').removeClass('hidden');
          } else {
            $('online-sponsorship').addClass('hidden');
          }
	}
      }.bind(this);
      this.page.tabbedContent.addEvent('onSelect', checkOnlineTab);
      checkOnlineTab();
    }

  },

  setupSubtabs: function() {
    var curr = this.el.getElement('.subtabs .current');
    var next = this.el.getElement('.subtabs .next');
    if (!curr || !next) {
      return;
    }
    curr.addEvent('click', function(e) {
      curr.addClass('subtab-selected');
      next.removeClass('subtab-selected');
      var subpane = curr.get('href').match(/#(.+)/)[1];
      this.el.getElement('.subpane.selected').removeClass('selected');
      this.el.getElement('.subpane.' + subpane).addClass('selected');
    }.bind(this));
    next.addEvent('click', function(e) {
      next.addClass('subtab-selected');
      curr.removeClass('subtab-selected');
      var subpane = next.get('href').match(/#(.+)/)[1];
      this.el.getElement('.subpane.selected').removeClass('selected');
      this.el.getElement('.subpane.' + subpane).addClass('selected');
    }.bind(this));
    this.subtabs.push(curr.get('href').match(/#(.+)/)[1]);
    this.subtabs.push(next.get('href').match(/#(.+)/)[1]);
  },

  setupCourses: function() {
    this.el.getElements('.course .view-detail').each(function(link) {
      link.addEvent('click', function(e) {
        new Event(e).stop();
        if (link.get('html').contains('View video')) {
          this.expandAndPlayVideo(link.getParent('.course'));
        } else {
          this.toggle(link);
        }
      }.bind(this));
    }.bind(this));
    this.el.getElements('.course .close').each(function(link) {
      link.addEvent('click', function(e) {
        new Event(e).stop();
        this.toggle(link);
        window.location = '#' + this.getLinkId(link);
      }.bind(this));
    }.bind(this));
    this.el.getElements('.course.with-video').forEach(function(el) {
      var button = new Element('a', {
        href: '#',
        'class': 'play-button',
        events: {
          click: function(e) {
            new Event(e).stop();
            this.expandAndPlayVideo(el);
          }.bind(this)
        }
      }).inject(el.getElement('.left'));
    }.bind(this));
    this.page.addEvent('onCourseExpanded', function(type) {
      if (typeof type === 'string' && type === 'video') {
        return;
      }
      this.el.getElements('iframe').forEach(function(iframe) {
        var src = iframe.get('src');
        if (src.match(/\?size=\w+/)) {
          src = src.replace(/\?size=\w+/, '');
        }
        iframe.src = src;
      }.bind(this));
    }.bind(this));
  },

  expandAndPlayVideo: function(el) {
    el.addClass('expanded');
    var embed = el.getElement('iframe');
    var src = embed.get('src');
    if (!src.match(/size=/)) {
      embed.src = src + '?size=full';
    }
    this.page.fireEvent('onCourseExpanded', ['video']);
  },

  setupCollapseExpandAll: function() {
    this.el.getElements('a.expand').addEvent('click', function(e) {
      new Event(e).stop();
      this.el.getElements('.course').addClass('expanded');
      this.page.fireEvent('onCourseExpanded');
    }.bind(this));
    this.el.getElements('a.collapse').addEvent('click', function(e) {
      new Event(e).stop();
      this.el.getElements('.course').removeClass('expanded');
      this.el.getElements('iframe').forEach(function(iframe) {
        var src = iframe.get('src');
        if (src.match(/\?size=\w+/)) {
          src = src.replace(/\?size=\w+/, '');
        }
        iframe.src = src;
      }.bind(this));
    }.bind(this));
  },

  setupPrint: function() {
    this.el.getElements('a.print').each(function(link) {
      link.addEvent('click', function(e) {
        new Event(e).stop();
        $$('div.introduction').addClass('print-hide');
        $$('.column-bc > .box').addClass('print-hide');
        $$('.course').addClass('print-hide');
        $$('.details-toggle').addClass('print-hide');
        $$('a.close').addClass('print-hide');
        $$('a.button-round-wrapper').addClass('print-hide');
        $$('a.print').addClass('print-hide');
        $$('a.share').addClass('print-hide');
        $$('.sIFR-replaced').addClass('print-hide');
        link.getParent('.course').removeClass('print-hide');
        window.print();
      });
    });
  },

  toggle: function(link) {
    var course = link.getParent('.course');
    course.toggleClass('expanded');
    if (course.hasClass('expanded')) {
      this.page.fireEvent('onCourseExpanded');
      var id = this.getLinkId(link);
      this.currentId = id;
      window.location = '#' + id;
    } else {
      if (course.getElement('iframe')) {
        course.getElement('iframe').src = course.getElement('iframe').get('src');
      }
    }
  },

  selectCourse: function(id) {
    var course = this.el.getElement('.course.' + id);
    if (course) {
      this.currentId = id;

      var classes = this.el.className.split(' ');
      classes.each(function(className) {
        if (className == "selected") {
          return;
        }
        if ($$('.JS_TabbedContent .tabs .' + className).length > 0) {
          this.page.tabbedContent.select(className);
        }
      }.bind(this));

      if (course.getParent('.subpane')) {
        classes = course.getParent('.subpane').className.split(' ');
        classes.each(function(className) {
          if (this.el.getElement('.subtabs .' + className)) {
            this.selectSubtab(className);
          }
        }.bind(this));
      }

      course.addClass('expanded');
      this.page.fireEvent('onCourseExpanded');

      if (this.justLoaded) {
        this.justLoaded = false;
        setTimeout(function() {
          new Fx.Scroll(window).toElement(course);
        }, 0);
      }
    }
  },

  selectSubtab: function(id) {
    var subpane = this.el.getElement('.subpane.' + id);
    var subtab = this.el.getElement('.subtabs .' + id);
    if (subpane && subtab) {
      this.el.getElements('.subpane.selected').removeClass('selected');
      this.el.getElements('.subtabs .subtab-selected').removeClass('subtab-selected');
      subpane.addClass('selected');
      subtab.addClass('subtab-selected');
      var parentId = id.replace(/-next/, '').replace(/-current/, '');
      this.page.tabbedContent.select(parentId);
    }
  },

  checkURL: function() {
    var hashId = this.getHashId();
    if (!hashId) {
      return;
    } else if (this.subtabs.contains(hashId)) {
      this.selectSubtab(hashId);
    } else if (this.currentId != hashId) {
      this.selectCourse(hashId);
    }
  },

  getHashId: function() {
    if (!window.location.hash || window.location.hash === '') {
      return;
    }
    var hashId = window.location.hash;
    if (hashId.substr(0, 1) == '#') {
      hashId = hashId.substr(1);
    }
    return hashId;
  },

  getLinkId: function(el) {
    return el.get('href').match(/#(.+)/)[1];
  }

});

MoMA.TimedContent = new Class({

  initialize: function(el) {
    if (el.timeCheck()) {
      el.setStyle('display', 'block');
    } else {
      el.addClass('hidden');
    }
  }

});

MoMA.MemberPreviewBadge = new Class({

  initialize: function(el) {
    this.el = el;
    if (!MoMA.memberPreviewToolTip) {
      MoMA.memberPreviewToolTip = new Element('div', {
        id: 'member-preview-tooltip'
      });
      MoMA.memberPreviewToolTip.inject(document.body);
    }
    if (!el.hasClass('member-preview-ps1')) {
      this.checkPreviewTime();
    }
    var memberPreviewHover = false;
    var parentLink = el.getParent('a');
    if (parentLink) {
      var origURL = parentLink.get('href');
    }
    el.addEvent('mouseenter', function() {
      var ps1URL = 'http://www.ps1.org/visit/';
      memberPreviewHover = true;
      if (parentLink) {
        parentLink.addClass('member-preview-hover');
        if (el.hasClass('member-preview-ps1')) {
          MoMA.memberPreviewToolTip.removeClass('early-hours');
          MoMA.memberPreviewToolTip.addClass('ps1');
          parentLink.set('href', ps1URL);
        } else if (el.hasClass('member-early-hours')) {
          MoMA.memberPreviewToolTip.removeClass('ps1');
          MoMA.memberPreviewToolTip.addClass('early-hours');
          parentLink.set('href', '/support/membership/join');
        } else {
          MoMA.memberPreviewToolTip.removeClass('ps1');
          MoMA.memberPreviewToolTip.removeClass('early-hours');
          parentLink.set('href', '/support/membership/join');
        }
      } else if (el.hasClass('member-preview-ps1')) {
        MoMA.memberPreviewToolTip.removeClass('early-hours');
        MoMA.memberPreviewToolTip.addClass('ps1');
        el.set('href', ps1URL);
      } else if (el.hasClass('member-early-hours')) {
        MoMA.memberPreviewToolTip.removeClass('ps1');
        MoMA.memberPreviewToolTip.addClass('early-hours');
        el.set('href', '/support/membership/join');
      } else {
        MoMA.memberPreviewToolTip.removeClass('ps1');
        MoMA.memberPreviewToolTip.removeClass('early-hours');
        el.set('href', '/support/membership/join');
      }

      MoMA.memberPreviewToolTip.fade('show');
    });
    el.addEvent('mouseleave', function() {
      MoMA.memberPreviewToolTip.fade('hide');
      memberPreviewHover = false;
      $('member-preview-tooltip').setStyle('left', -1000);
      if (parentLink) {
        parentLink.removeClass('member-preview-hover');
        parentLink.set('href', origURL);
      }
    });
    $(document).addEvent('mousemove', function(e) {
      if (MoMA.memberPreviewToolTip && memberPreviewHover) {

        var w = MoMA.memberPreviewToolTip.getSize().x;
        var h = MoMA.memberPreviewToolTip.getSize().y;
        var x = e.page.x + 10;
        var y = e.page.y;
        if (e.page.x + 10 + w > window.getSize().x) {
          // Flip horizontally
          x = e.page.x - 12 - w;
        }
        if (e.page.y + h - window.getScroll().y > window.getSize().y) {
          // Flip vertically
          y = e.page.y - h + 20;
        }
        MoMA.memberPreviewToolTip.setStyles({
          left: x,
          top: y
        });
      }
    });
  },

  checkPreviewTime: function() {
    if (this.el.className.match(/preview(\d+)/)) {
      var previewTimestamp = this.el.className.match(/preview(\d+)/)[1];
      var previewDate = new Date(previewTimestamp * 1000);
      var now = new Date();
      if (previewDate.getTime() > now.getTime()) {
        if (this.el.hasClass('member-preview-abbreviated') || this.el.getParent('.size-2x2') || this.el.getParent('.size-1x3')) {
          var month = previewDate.format('%m');
          if (month.substr(0, 1) == '0') {
            month = month.substr(1);
          }
          this.el.set('text', 'PREVIEWS START ' + month + '/' + parseInt(previewDate.format('%d'), 10));
        } else {
          this.el.set('html', 'MEMBER PREVIEWS START ' + previewDate.format('%B ').toUpperCase() + parseInt(previewDate.format('%d'), 10));
        }
      }
    }
  }

});

MoMA.BlogIndex = new Class({

  initialize: function(el) {
    el.getElements('.blog-content').each(function(post) {
      var attachment = post.getElement('.wp-caption');
      if (attachment && attachment.getSize().y > post.getSize().y) {
        var clear = new Element('br', {
          'class': 'clear'
        });
        clear.inject(post);
      }
    });
  }

});

MoMA.ENewsForm = new Class({

  initialize: function(el) {
    var left = el.getElements('.interests input[type=checkbox]');
    var right = el.getElements('.quick-picks input[type=checkbox]');
    left.each(this.syncCheckboxes);
    right.each(this.syncCheckboxes);
  },

  syncCheckboxes: function(checkbox, index) {
    checkbox.addEvent('change', function() {
      var match = checkbox.className.match(/checkbox\d+/);
      if (match) {
        $$('.' + match[0]).each(function(cb) {
          cb.checked = checkbox.checked;
        });
      }
    });
  }

});

MoMA.SocialTabs = new Class({

  initialize: function(el) {
    this.el = el;
    this.setupTabs();
    this.checkCookie();
  },

  setupTabs: function() {
    this.el.getElements('.tabs a').each(function(link) {
      link.addEvent('click', function(e) {
        new Event(e).stop();
        this.selectTab(link);
      }.bind(this));
    }.bind(this));
  },

  checkCookie: function() {
    var social = Cookie.read('home-social-tab') || 'twitter';
    var link = this.el.getElement('.tabs a.' + social);
    this.selectTab(link);
  },

  selectTab: function(link) {
    $$('#social .selected').removeClass('selected');
    link.addClass('selected');
    var target = link.get('data-target');
    $(target).addClass('selected');
    if (target == 'social-facebook' && !this.facebookLoaded) {
      this.loadFacebook();
      this.facebookLoaded = true;
    } else if (target == 'social-twitter' && !this.twitterLoaded) {
      this.loadTwitter();
      this.twitterLoaded = true;
    }
    Cookie.write('home-social-tab', target.replace('social-', ''), {
      duration: 365
    });
  },

  loadTwitter: function() {
    var script = Asset.javascript('//platform.twitter.com/widgets.js');
    script.id = 'twitter-wjs';
    //<script>!function(d,s,id){var js,fjs=d.getElementsByTagName(s)[0];if(!d.getElementById(id)){js=d.createElement(s);js.id=id;js.src="//platform.twitter.com/widgets.js";fjs.parentNode.insertBefore(js,fjs);}}(document,"script","twitter-wjs");</script>
  },

  loadFacebook: function() {
    new Element('div', {
      id: 'fb-root'
    }).inject(document.body);
    var script = Asset.javascript('//connect.facebook.net/en_US/all.js#xfbml=1&appId=115458276660');
    script.id = 'facebook-jssdk';
    /*
    <div id="fb-root"></div>
    <script>(function(d, s, id) {
      var js, fjs = d.getElementsByTagName(s)[0];
      if (d.getElementById(id)) return;
      js = d.createElement(s); js.id = id;
      js.src = "//connect.facebook.net/en_US/all.js#xfbml=1&appId=115458276660";
      fjs.parentNode.insertBefore(js, fjs);
    }(document, 'script', 'facebook-jssdk'));</script>*/
  }

});

MoMA.HomePaginated = new Class({

  initialize: function(el) {
    this.el = el;
    this.setupPages();
    this.setupNavigation();
  },

  setupPages: function() {
    var extantList = this.el.getElement('ul');
    var extantItems = this.el.getElements('li');
    var activeItems = [];
    extantItems.each(function(item) {
      if (item.timeCheck()) {
        activeItems.push(item);
      }
    });
    var slider = new Element('div', {
      'class': 'slider'
    }).inject(this.el);
    var page;
    activeItems.each(function(item, index) {
      if (index % 3 == 0) {
        page = new Element('div', {
          'class': 'page',
          html: '<ul></ul>'
        }).inject(slider);
      }
      item.inject(page.getElement('ul'));
    });
    new Element('div', {
      'class': 'clear'
    }).inject(slider);
    extantList.destroy();
  },

  setupNavigation: function() {
    var pages = this.el.getElements('.page');
    if (pages.length < 2) {
      return;
    }
    var width = this.el.getSize().x;
    this.el.getElement('.slider').setStyle('width', width * pages.length);
    var pagination = new Element('div', {
      'class': 'pagination'
    }).inject(this.el);
    for (var i = 0; i < pages.length; i++) {
      this.setupPaginationLink(pagination, i);
    }
    this.el.getElement('.slider').set('tween', {
      duration: 500,
      transition: Fx.Transitions.Quart.easeOut
    });
  },

  setupPaginationLink: function(pagination, i) {
    var selected = (i == 0) ? ' selected' : '';
    var link = new Element('a', {
      'class': 'page' + selected,
      href: '#',
      events: {
        click: function(e) {
          e.stop();
          this.selectPage(i);
        }.bind(this)
      }
    }).inject(pagination);
  },

  selectPage: function(page) {
    this.el.getElements('.pagination .selected').removeClass('selected');
    var selectedPage = this.el.getElements('.pagination .page')[page];
    selectedPage.addClass('selected');
    this.el.getElement('.slider').tween('left', this.el.getSize().x * -page);
  }

});

MoMA.MoMAAudio = new Class({

  initialize: function(el) {
    if (typeof el.get('data-language') == 'string' && el.get('data-language').match(/(\w\w)-(\w\w)/)) {
      var lang = el.get('data-language').match(/(\w\w)-(\w\w)/)[1];
      $$('.audio-category').each(function(category) {
        var list = category.getElement('ul');
        if (category.getElement('.' + lang)) {
          category.getElement('.' + lang).inject(list, 'top');
          var link = category.getElement('.' + lang).getElement('a');
          category.getElement('img').getParent('a').set('href', link.get('href'));
        }
      });
    }
  }

});

function setupTextSize() {
  var maxSize = 3;
  var minSize = -3;
  var smaller = $$('a.text-smaller');
  var larger = $$('a.text-larger');
  if (smaller.length != 1 || larger.length != 1) {
    return;
  }
  smaller = smaller[0];
  larger = larger[0];
  var size = Cookie.read('text_size') || 0;

  if (size == maxSize) {
    larger.addClass('disabled');
  } else if (size == minSize) {
    smaller.addClass('disabled');
  }

  smaller.addEvent('click', function() {
    if (size != minSize) {
      size--;
      Cookie.write('text_size', size);
      var css = new Asset.css('/stylesheets/text_size' + size + '.css');
      if (size == minSize) {
        smaller.addClass('disabled');
      }
      larger.removeClass('disabled');
    }
    return false;
  });

  larger.addEvent('click', function() {
    if (size != maxSize) {
      size++;
      Cookie.write('text_size', size);
      var css = new Asset.css('/stylesheets/text_size' + size + '.css');
      if (size == maxSize) {
        larger.addClass('disabled');
      }
      smaller.removeClass('disabled');
    }
    return false;
  });
}

function setupMenuControls() {
  $$('#menu a.toggle').each(function(link) {
    var parent = link.getParent('li');
    var slide = new Fx.Slide(parent.getElement('ul'), {
      duration: 'short'
    });
    if (!parent.hasClass('selected')) {
      slide.hide();
    } else {
      link.set('html', '&ndash;');
      link.addClass('expanded');
    }
    link.addEvent('click', function(e) {
      new Event(e).stop();
      slide.toggle().chain(function() {
        link.toggleClass('expanded');
      });
    });
  });
  $$('#menu > li > a').each(function(link) {
    link.addEvent('mouseover', function() {
      link.getParent('li').addClass('hovered');
    });
    link.addEvent('mouseout', function() {
      link.getParent('li').removeClass('hovered');
    });
  });
}

function injectBreadcrumb() {
  if ($('top-nav') && $('top-nav').getElement('.breadcrumbs.feed-me') && $('breadcrumbs-content')) {
    var el = $('top-nav').getElement('.breadcrumbs');
    el.fade('hide');
    el.set('html', $('breadcrumbs-content').get('html'));
    el.fade('in');
    el.removeClass('feed-me');
    $('breadcrumbs-content').destroy();
  }
}

function checkBreadcrumbCapitalization() {
  $$('#top-nav .breadcrumbs a').each(function(link) {
    if (link.get('id') == 'home-ticker') {
      return;
    }
    var html = link.get('html').toUpperCase();
    if (html.contains('MOMA')) {
      link.set('html', html.replace('MOMA', 'MoMA'));
      link.setStyle('text-transform', 'none');
    }
  });
}

function setupSuperNav() {
  if ($('share-page')) {
    $('share-page').getElement('a').addEvent('mouseenter', function() {
      $('user-dropdown').addClass('gray');
    });
    $('share-page').getElement('a').addEvent('mouseleave', function() {
      $('user-dropdown').removeClass('gray');
    });
  }
  if ($('user-dropdown')) {
    new Request({
      url: '/users/user_dropdown',
      onComplete: function(html) {
        var links = $('top-nav').getElement('.right');
        links.setStyle('display', 'block');
        links.fade('hide');
        $('user-dropdown').set('html', html);
        $('share-page').addClass('ready');
        links.fade('in');
        if ($('user-options')) {
          $(document.body).addClass('logged-in');
        }
        MoMA.fireEvent('userUpdate');
      }
    }).send();
    $('user-dropdown').addEvent('mouseenter', function() {
      $('user-dropdown').addClass('hover');
    });
    $('user-dropdown').addEvent('mouseleave', function() {
      $('user-dropdown').removeClass('hover');
    });
  }
}

function toggleSavedObject(link, object_id, callback) {
  var action = link.hasClass('remove') ? 'destroy' : 'create';
  var request = new Request({
    url: "/shiftspace/saved_objects/" + action + ".json",
    onComplete: function() {
      if (typeof callback == 'function') {
        callback(link);
      }
    },
    onSuccess: function() {
      link.toggleClass('remove');
      if (link.hasClass('remove')) {
        link.set('html', 'Remove');
        link.set('title', 'Remove from My Collection');
      } else {
        link.set('html', 'Save');
        link.set('title', 'Add to My Collection');
      }
    },
    onError: function() {
      if (action == 'create') {
        alert('There was an error adding this object to your collection.');
      } else {
        alert('There was an error removing this object from your collection.');
      }
    }
  }).post({
    object_id: object_id
  });
}

function setupAddRemoveObjects() {
  var ids = [];
  var links = {};
  $$('.ss-add-item').each(function(link) {
    if (link.hasClass('setup')) {
      return;
    }
    link.addClass('setup');
    link.removeClass('ss-no-text');
    link.set('html', 'Save');
    var object_id = link.get('rel').match(/(\d+)\.json$/)[1];
    ids.push(object_id);
    links[object_id] = link;
  });
  if (ids.length > 0) {
    var req = new Request({
      url: '/explore/collection/objects_check.json',
      onSuccess: function(json) {
        var objects = JSON.decode(json);
        ids.each(function(id) {
          var link = links[id];
          var object_id = link.get('rel').match(/(\d+)\.json$/)[1];
          link.setStyle('display', 'block');
          if (objects[id] == 'inactive') {
            links[id].addEvent('click', function(e) {
              new Event(e).stop();
              alert('Sorry, this object is not available to be saved right now. Please try again later.');
            });
          } else {
            if (objects[id] == 'saved') {
              links[id].addClass('remove');
              links[id].set('html', 'Remove');
            }
            link.addEvent('click', function(e) {
              new Event(e).stop();
              if ($(document.body).hasClass('logged-in')) {
                toggleSavedObject(link, object_id);
              } else {
                if (confirm('Sorry, you must be logged in to save works to My Collection. Would you like to log in now?')) {
                  window.location = '/login';
                }
              }
            });
          }
        });
      }
    }).post({
      ids: ids.join(',')
    });

  }
}

function setupWhatsNewHere() {
  if (!$('bottom-nav')) {
    return;
  }
  var holder = $('bottom-nav').getElement('.holder');
  var div = new Element('div', {
    id: 'whats-new-here',
    html: '<a href="/login" class="trigger">What’s new here?</a>' +
          '<div class="whats-new-info"><p>We are building a new site for MoMA members and enhancing the sharing and saving features on MoMA.org. During this process some features may be temporarily unavailable. Please note that the log-in button has moved to the upper-right corner of the screen.</p><p class="login"><a href="/login">Log in or register</a> to see more.</a></p>'
  });
  div.inject(holder);
  div.addEvent('mouseenter', function() {
    div.addClass('hover');
  });
  div.addEvent('mouseleave', function() {
    div.removeClass('hover');
  });
}

function checkCopyrightYear() {
  if ($('footer')) {
    var link = $('footer').getElement('a.copyright');
    if (link) {
      var year = new Date().format('%Y');
      if (!link.get('html').contains('&copy; ' + year)) {
        link.set('html', '&copy; ' + year + ' The Museum of Modern Art');
      }
    }
  }
}

MoMA.addEvent('onBeforeInitialize', function() {
  massageAddItemColors();
  setupTextSize();
  setupMenuControls();
  injectBreadcrumb();
  checkBreadcrumbCapitalization();
  setupSuperNav();
  setupAddRemoveObjects();
  //setupWhatsNewHere();
});

MoMA.addEvent('onAfterInitialize', function() {
  checkCopyrightYear();
});

function updateNavPosition() {
  var size = $(window).getSize();
  var navHeight = 78;
  var target = size.y - navHeight + $(window).getScroll().y;
  var current = $('nav').getPosition().y;
  if (target != current) {
    $('nav').setStyle('top', target);
  }
}

function showUpgradeMessage() {
  $('browser-support').addClass('terse');
  $('browser-support').removeClass('hidden');
}

function isFirefox() {
  return (Browser.Engine.gecko || (navigator && navigator.userAgent && navigator.userAgent.indexOf('Firefox') != -1));
}

function isSafari() {
  // Safari 3 = webkit 525
  return (Browser.Engine.webkit);
}

function isIE7() {
  return (Browser.Engine.trident && Browser.Engine.version > 4);
}

function isIE6() {
  return (Browser.Engine.trident && Browser.Engine.version < 5);
}

function isOpera() {
  return (Browser.Engine.presto);
}

function massageAddItemColors() {
  // In the collection list view set a class based on the user's color selection
  if ($('list-view-items')) {
    var colors = $$('.options .colors');
    if (colors.length === 0) {
      return;
    }
    var images = colors[0].getElements('img');
    if (images.length < 3) {
      return;
    }
    if (images[1].get('src').contains('grey_btn_on')) {
      $('list-view-items').addClass('ss-medium');
    } else if (images[2].get('src').contains('black_btn_on')) {
      $('list-view-items').addClass('ss-dark');
    }
  }
}

function isTouchUI() {
  return !!('ontouchstart' in window)
         || !!('onmsgesturechange' in window);
}

var dbug = {
  enable: $empty,
  log: function() {
    if (typeof console == 'object') {
      for (var i = 0; i < arguments.length; i++) {
        console.log(arguments[i]);
      }
    }
  }
};

// From hunlock.com
Array.prototype.shuffle = function () {
  for (var rnd, tmp, i = this.length; i; rnd = parseInt(Math.random()*i, 10), tmp=this[--i], this[i]=this[rnd], this[rnd]=tmp) {
  }
};

// **************************************************************************
// Copyright 2007 - 2009 Tavs Dokkedahl
// Contact: http://www.jslab.dk/contact.php
//
// This file is part of the JSLab Standard Library (JSL) Program.
//
// JSL is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 3 of the License, or
// any later version.
//
// JSL is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program. If not, see <http://www.gnu.org/licenses/>.
// ***************************************************************************

// Return new array with duplicate values removed
Array.prototype.unique =
  function() {
    var a = [];
    var l = this.length;
    for(var i=0; i<l; i++) {
      for(var j=i+1; j<l; j++) {
        // If this[i] is found later in the array
        if (this[i] === this[j]) {
          j = ++i;
        }
      }
      a.push(this[i]);
    }
    return a;
  };


Element.implement({

  shorten: function(height) {
    var text = this.get('html');
    var closingTags = text.match(/<\/[^>]+>/g);
    closingTags = closingTags ? closingTags.join('') : '';
    var length = text.length;
    var revert = this.expose();
    while (this.getSize().y > height) {
      length--;
      this.set('html', text.substr(0, length) + '&hellip;' + closingTags);
    }
    revert();
  },

	// From sajithmr.com
  isLoaded: function() {
    if (this.nodeName.toLowerCase() != 'img') {
      return true;
    }
    if (!this.complete) {
      return false;
    }
    if (typeof this.naturalWidth != "undefined" &&
        this.naturalWidth === 0) {
      return false;
    }
    return true;
  },

  timeCheck: function() {
    var startMatch = this.className.match(/start(\d+)/);
    var endMatch = this.className.match(/end(\d+)/);
    var start, end, now = new Date();
    if (this.get('data-start')) {
      start = Date.parse(this.get('data-start'));
    }
    if (this.get('data-end')) {
      end = Date.parse(this.get('data-end'));
    }
    if (startMatch && endMatch) {
      start = new Date(parseInt(startMatch[1], 10) * 1000);
      end = new Date(parseInt(endMatch[1], 10) * 1000);
    }
    if (start && now < start || end && now > end) {
      return false;
    }
    return true;
  }

});

function log() {
  if (typeof console != 'undefined') {
    for (var i = 0; i < arguments.length; i++) {
      console.log(arguments[i]);
    }
  }
}

function updateHeight(target, height) {
  $(target).setStyle('height', height);
}

/* Viper's Video Quicktags */
var vvqflashvars = {};
var vvqparams = { wmode: "opaque", allowfullscreen: "true", allowscriptacess: "always" };
var vvqattributes = {};
var vvqexpressinstall = "/explore/inside_out/main/wp-content/plugins/vipers-video-quicktags/resources/expressinstall.swf";

var overlay = location.search.match(/overlay=([^&]+)/);
if (location.search.indexOf('ref=behance') != -1) {
  overlay = [null, 'behance'];
}
if (overlay) {
  overlay = overlay[1];
  if (overlay.match(/^(.+)\.(\d+)\.(\d+)$/)) {
    var packageId = overlay.match(/^(.+)\.(\d+)\.(\d+)$/)[2];
    var assetId =  overlay.match(/^(.+)\.(\d+)\.(\d+)$/)[3];
    overlay = overlay.match(/^(.+)\.(\d+)\.(\d+)$/)[1];
  }
  Asset.css('/javascripts/squeezebox/SqueezeBox.css');
  Asset.css('/stylesheets/overlay.css');
  Asset.javascript('/javascripts/squeezebox/SqueezeBox.js', {
    onLoad: function() {
      Asset.javascript('/javascripts/overlay.js', {
        onLoad: function() {
          new Element('div', {
            html: '<div id="overlay"></div>',
            'class': 'pre-injection'
          }).inject(document.body);
          Asset.image('/images/promotions/overlays/' + overlay + '.jpg', {
            onLoad: function() {
              var overlay = new Overlay($('overlay'), {
                initDelay: 500,
                overlayOpacity: 0.6
              });
              if (packageId && assetId) {
                overlay.addEvent('setupMarkup', function() {
                  new Element('div', {
                    styles: {
                      position: 'absolute',
                      left: 32,
                      top: 135
                    },
                    html: '<iframe src="http://www.moma.org/videos/embed/' + packageId + '/' + assetId + '?size=full" width="450" height="253" frameborder="0" allowfullscreen="allowfullscreen"></iframe>'
                  }).inject(overlay.el);
                });
              }
              overlay.show();
              $('overlay').addEvent('click', function() {
                overlay.hide();
              });
            }
          }).inject($('overlay'));
        }
      });
    }
  });
}
