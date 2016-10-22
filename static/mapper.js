

function h(sel, ...args) {
  const el = h.createElement(sel)
  h.add(el, args)
  return el
}
Object.assign(h, {
  _views: [],
  _view: null,

  pushView(v) {
    if (h._view) h._views.push(h._view)
    h._view = v
  },
  popView(v) {h._view = h._views.pop()},

  nearest(sel, el, stop) {
    while (el && el.nodeType === 1 && el !== stop) {
      if (el.matches(sel)) return el
      el = el.parentNode
    }
  },
  nextSkippingChildren(x) {
    for (; x; x = x.parentNode) if (x.nextSibling) return x.nextSibling
  },

  createElement(sel) {
    const parts = (sel || '').split(/([#.])/)
    const el = document.createElement(parts[0] || 'div')
    const l = parts.length
    if (l > 1) {
      const classes = []
      for (let i = 1; i < l; i += 2) {
        if (parts[i] === '#') el.id = parts[i + 1]
        else classes.push(parts[i + 1])
      }
      el.className = classes.join(' ')
    }
    return el
  },
  add(el, a) {
    if (Array.isArray(a)) {
      for (const c of a) h.add(el, c)
    } else if (typeof a === 'object' && a) {
      if (a.isView) h._view.add(a, el)
      else if (a.tagName) el.appendChild(a)
      // else if (a.then) h.addPromise(el, a)
      else h.attrs(el, a)
    } else {
      el.appendChild(document.createTextNode(String(a)))
    }
  },
  // addPromise(el, a) {
  //   function replace(a) {
  //     if (Array.isArray(a)) {
  //       for (const c of a) h.add(f, c)
  //     } else if (typeof a === 'object' && a) {
  //       if (a.isView) h._view.add(a, el)
  //       else if (a.tagName) el.appendChild(a)
  //       else if (a.then) h.addPromise(el, a)
  //       else h.attrs(el, a)
  //     } else {
  //       el.appendChild(document.createTextNode(String(a)))
  //     }
  //   }
  //   const tn = document.createTextNode('')
  //   el.appendChild(tn)
  //   a.then(replace)
  // },
  attrs(el, a) {
    for (const k in a) {
      const v = a[k]
      if (typeof v === 'object') h.attrs(el[k], v)
      else if (k.startsWith('on')) el.addEventListener(k.slice(2), typeof v === 'string' ? h._view[v].bind(h._view) : v)
      else el[k] = v
    }
  },

  removeChildren(el) {while (el.firstChild) el.removeChild(el.lastChild)},
})

/*****************************************************************************/

function extend(src, dest) {
  src = src || {};
  dest = dest || {};
  for (var key in src) {
    if (src.hasOwnProperty(key) && !dest.hasOwnProperty(key)) {
      dest[key] = src[key];
    }
  }
  return dest;
}

function capitalize(x) {
  if (x === null || x === undefined) return '';
  x = ''+x;
  return x[0].toUpperCase() + x.slice(1).toLowerCase();
}

function encodeParam(item) {
  // encodeURIComponent is conservative, since it doesn't know which component it's escaping.
  return (item || '').replace(/[%\x00-\x1f\x20"#<>?`{};^|\u007f-\uffff&]+/g, function(x) {
    return encodeURIComponent(x);
  });
}

function parseQuery(search) {
  var search = search.slice(1); // ignore ?
  var parts = search.split('&');
  var args = {};
  for (var i=0; i<parts.length; i++) {
    var words = parts[i].split('=');
    var key = decodeURIComponent(words[0]);
    var value = words[1] ? decodeURIComponent(words[1]) : undefined;
    args[key] = value;
  }
  return args;
}

function keyBy(key, items) {
  var d = {};
  for (var i=0; i<items.length; i++) {
    var item = items[i];
    d[item[key]] = item;
  }
  return d;
}

function values(d) {
  return Object.keys(d).map(function(key) {
    return d[key];
  });
}

var get = function(url, cb) {
  var xhr = new XMLHttpRequest;
  xhr.open('GET', url, true);
  xhr.addEventListener('load', function() {
    if (xhr.status !== 200) throw "XHR Error: " + xhr.status;
    cb(JSON.parse(xhr.responseText));
  });
  xhr.send();
};

var post = function(url, obj, cb) {
  var xhr = new XMLHttpRequest;
  xhr.open('POST', url, true);
  xhr.addEventListener('load', function() {
    if (xhr.status !== 200) throw "XHR Error: " + xhr.status;
    var text = xhr.responseText;
    try {
      var data = JSON.parse(text);
    } catch (e) {}
    if (data && data.ok === true) { // TODO not this
      cb(data);
    } else {
      alert(text);
    }
  });
  xhr.setRequestHeader('Content-Type', 'application/json;charset=UTF-8');
  var data = JSON.stringify(obj);
  xhr.send(data);
};

/*****************************************************************************/

/* drag in files */
// TODO allow dragging anywhere in window

function cancel(e) {
  e.preventDefault();
  if (e.dataTransfer) e.dataTransfer.dropEffect = 'copy';
}
document.body.addEventListener('dragover', cancel);
document.body.addEventListener('dragenter', cancel);

function dragIn(e) {
  document.body.classList.add('drag-target');
}
document.body.addEventListener('dragenter', dragIn);
document.body.addEventListener('dragover', dragIn);

function dragEnd(e) {
  document.body.classList.remove('drag-target');
}
document.body.addEventListener('dragend', dragEnd);
document.body.addEventListener('dragexit', dragEnd);
document.body.addEventListener('dragleave', dragEnd);
document.body.addEventListener('drop', dragEnd);

document.body.addEventListener('drop', function(e) {
  e.preventDefault();

  loadFiles(e.dataTransfer.files);
});

function loadFiles(files) {
  var fractions = [];
  var done = 0;

  for (var i=0; i<files.length; i++) {
    var file = files[i];

    var reader = new FileReader();
    var xhr = new XMLHttpRequest();

    xhr.upload.addEventListener('progress', function(e) {
      if (e.lengthComputable) {
        fractions[i] = e.loaded / e.total;
        update();
      }
    }, false);

    xhr.upload.addEventListener('load', function(e) {
      fractions[i] = 1;
      update();
    }, false);

    xhr.addEventListener('load', function(e) {
      if (xhr.readyState === 4 && xhr.status === 200) {
        var text = xhr.responseText;
        if (text) {
          update();

          // HERE happens the things
          visualizeParty(text);
        }
      }
      done++;
      update();
    });
    // TODO handle XHR errors?

    xhr.open('POST', '/upload?filename=' + encodeURIComponent(file.name));
    xhr.responseType = 'text';
    xhr.overrideMimeType('application/octet-stream');
    reader.onload = function(evt) {
      xhr.send(evt.target.result);
    };
    reader.readAsBinaryString(file);
  }

  function update() {
    var sum = 0;
    for (i in fractions) {
      sum += fractions[i];
    }
    setProgress(sum, (done === files.length));
  }
}

var progress = document.createElement('div');
progress.className = 'progress';
progress.style.opacity = 0;
document.body.appendChild(progress);

function setProgress(frac, done) {
  if (!done) {
    progress.style.opacity = 1;
  } else {
    setTimeout(function() {
      progress.style.opacity = 0;
    }, 100);
  }
  progress.style.width = (frac * 100) + '%';
}

document.body.addEventListener('keydown', function(e) {
  if (e.keyCode === 27) {
    clearSelection();
  }
});


// choose a file button

var loadBtn = document.querySelector('#file-picker');
var fileInput = h('input', { type: 'file', });
loadBtn.appendChild(fileInput);

function handleFileSelect(e) {
  loadFiles(e.target.files);
}
fileInput.addEventListener('change', handleFileSelect, false);


/*****************************************************************************/

/* for constructing SVGs */

var xml = new DOMParser().parseFromString('<xml></xml>',  'application/xml');
function cdata(content) {
  return xml.createCDATASection(content);
}

function el(name, props) {
  var el = document.createElementNS('http://www.w3.org/2000/svg', name);
  if (name === 'svg') {
    // explicit set namespace, see https://github.com/jindw/xmldom/issues/97
    el.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
    el.setAttribute('xmlns:xlink', 'http://www.w3.org/1999/xlink');
  }
  return setProps(el, props);
}

var directProps = {
  textContent: true,
};
function setProps(el, props) {
  for (var key in props) {
    var value = '' + props[key];
    if (directProps[key]) {
      el[key] = value;
    } else if (props[key] !== null && props.hasOwnProperty(key)) {
      el.setAttribute(key, value);
    }
  }
  return el;
}

function withChildren(el, children) {
  for (var i=0; i<children.length; i++) {
    el.appendChild(children[i]);
  }
  return el;
}

function group(children) {
  return withChildren(el('g'), children);
}

function newSVG(width, height) {
  return el('svg', {
    version: '1.1',
    width: width,
    height: height,
  });
}

function polygon(props) {
  return el('polygon', extend(props, {
    points: props.points.join(' '),
  }));
}

function path(props) {
  return el('path', extend(props, {
    path: null,
    d: props.path.join(' '),
  }));
}

function text(x, y, content, props) {
  var text = el('text', extend(props, {
    x: x,
    y: y,
    textContent: content,
  }));
  return text;
}

function symbol(href) {
  return el('use', {
    'xlink:href': href,
  });
}

function move(dx, dy, el) {
  setProps(el, {
    transform: ['translate(', dx, ' ', dy, ')'].join(''),
  });
  return el;
}

function translatePath(dx, dy, path) {
  var isX = true;
  var parts = path.split(' ');
  var out = [];
  for (var i=0; i<parts.length; i++) {
    var part = parts[i];
    if (part === 'A') {
      var j = i + 5;
      out.push('A');
      while (i < j) {
        out.push(parts[++i]);
      }
      continue;
    } else if (/[A-Za-z]/.test(part)) {
      assert(isX);
    } else {
      part = +part;
      part += isX ? dx : dy;
      isX = !isX;
    }
    out.push(part);
  }
  return out.join(' ');
}


/* shapes */

function rect(w, h, props) {
  return el('rect', extend(props, {
    x: 0,
    y: 0,
    width: w,
    height: h,
  }));
}

function bbRect(bbox) {
  var bot = bbox[0], top = bbox[1], left = bbox[2], right = bbox[3];
  var width = right - left;
  var height = top - bot;
  return el('rect', {
    x: left,
    y: -top,
    width: right - left,
    height: top - bot,
  });
}

/* definitions */

var cssContent = `
`;

function makeStyle() {
  var style = el('style');
  style.appendChild(cdata(cssContent));
  return style;
}

var Filter = function(id, props) {
  this.el = el('filter', extend(props, {
    id: id,
    x0: '-50%',
    y0: '-50%',
    width: '200%',
    height: '200%',
  }));
  this.highestId = 0;
};
Filter.prototype.fe = function(name, props, children) {
  var shortName = name.toLowerCase().replace(/gaussian|osite/, '');
  var id = [shortName, '-', ++this.highestId].join('');
  this.el.appendChild(withChildren(el('fe' + name, extend(props, {
    result: id,
  })), children || []));
  return id;
};
Filter.prototype.comp = function(op, in1, in2, props) {
  return this.fe('Composite', extend(props, {
    operator: op,
    in: in1,
    in2: in2,
  }));
};
Filter.prototype.subtract = function(in1, in2) {
  return this.comp('arithmetic', in1, in2, { k2: +1, k3: -1 });
};
Filter.prototype.offset = function(dx, dy, in1) {
  return this.fe('Offset', {
    in: in1,
    dx: dx,
    dy: dy,
  });
};
Filter.prototype.flood = function(color, opacity, in1) {
  return this.fe('Flood', {
    in: in1,
    'flood-color': color,
    'flood-opacity': opacity,
  });
};
Filter.prototype.blur = function(dev) {
  return this.fe('GaussianBlur', {
    'in': 'SourceAlpha',
    stdDeviation: [dev, dev].join(' '),
  });
};
Filter.prototype.merge = function(children) {
  this.fe('Merge', {}, children.map(function(name) {
    return el('feMergeNode', {
      in: name,
    });
  }));
};

/*****************************************************************************/

var left = document.querySelector('.left.col');
var right = document.querySelector('.right.col');

function visualizeParty(text) {
  var json = JSON.parse(text);
  var headings = json.headings;
  var records = json.records;
  var bbox = json.bbox;

  console.log(json);

  console.log(left);
  console.log(right);
  left.innerHTML = '';
  right.innerHTML = '';

  // create shapes.
  var w = left.clientWidth;
  var svg = newSVG(w, w);
  svg.appendChild(makeStyle());
  left.appendChild(svg);

  var title, subtitle;
  right.appendChild(title = h('h2', h('em', "Tap the map...")));
  right.appendChild(subtitle = h('p.subtitle', ""));

  var paths = [];
  records.forEach(function(record) {
    var path;
    paths.push(path = el('path', {
      d: record.region.simple_path,
    }));
    var activate = function() {
      console.log(record);
      title.textContent = record.query;
      subtitle.textContent = record.region.name;
    };
    path.addEventListener('mouseover', activate);
    path.addEventListener('touchdown', activate);

    paths.push(bbRect(record.region.boundingbox));
  });
  var world = group(paths);

  // TODO pan, zoom
  world.style.transformOrigin = 'center';

  var sw = w;
  var sh = w;
  var width = bbox[3] - bbox[2];
  var height = bbox[1] - bbox[0];
  if (width < 0) throw 'poo';
  if (height < 0) throw 'poo';
  var scale = Math.min(sw / width, sh / height);
  //world.appendChild(bbRect(bbox));

  // Where is the bounding box center?
  var x = (bbox[2] + bbox[3]) / 2;
  var y = (bbox[0] + bbox[1]) / 2 + 100;

  var p = 'translate('+x+'px, '+y+'px) scale(' + scale + ')';
  world.style.transform = p;

  var foo = group([world]);
  foo.style.transform = 'translate(' + (sw/2) + 'px, ' + (sh/2) + 'px)';

  svg.appendChild(foo);

  debugger;
}

