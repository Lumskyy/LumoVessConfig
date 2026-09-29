function copyText(t) {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    return navigator.clipboard.writeText(t);
  }
  return new Promise(function (resolve) {
    var ta = document.createElement("textarea");
    ta.value = t;
    document.body.appendChild(ta);
    ta.select();
    try {
      document.execCommand("copy");
    } catch (e) {
    }
    document.body.removeChild(ta);
    resolve();
  });
}

function bindCopy() {
  var btns = document.querySelectorAll("[data-copy]");
  for (var i = 0; i < btns.length; i++) {
    (function (b) {
      b.addEventListener("click", function () {
        copyText(b.getAttribute("data-copy"));
        b.textContent = "Copied";
        setTimeout(function () { b.textContent = "Copy"; }, 1200);
      });
    })(btns[i]);
  }
  var p = document.getElementById("copypattern");
  if (p) {
    p.addEventListener("click", function () {
      var el = document.getElementById("countrypattern");
      copyText(el ? el.textContent : "");
      p.textContent = "Copied";
      setTimeout(function () { p.textContent = "Copy"; }, 1200);
    });
  }
}

function setText(id, v) {
  var el = document.getElementById(id);
  if (el) {
    el.textContent = v;
  }
}

var NAMES = {US:"United States",JP:"Japan",SG:"Singapore",NL:"Netherlands",DE:"Germany",GB:"United Kingdom",FR:"France",CA:"Canada",HK:"Hong Kong",TW:"Taiwan",KR:"South Korea",AU:"Australia",IN:"India",BR:"Brazil",TR:"Turkey",FI:"Finland",SE:"Sweden",NO:"Norway",PL:"Poland",IT:"Italy",ES:"Spain",CH:"Switzerland",AT:"Austria",IE:"Ireland",RO:"Romania",UA:"Ukraine",KZ:"Kazakhstan",AE:"UAE",IR:"Iran",RU:"Russia",MY:"Malaysia",ID:"Indonesia",TH:"Thailand",VN:"Vietnam",PH:"Philippines",MX:"Mexico",AR:"Argentina",CL:"Chile",CO:"Colombia",ZA:"South Africa",EG:"Egypt",IL:"Israel",GR:"Greece",PT:"Portugal",CZ:"Czechia",HU:"Hungary",DK:"Denmark",BE:"Belgium",LV:"Latvia",LT:"Lithuania",EE:"Estonia",HR:"Croatia",RS:"Serbia",BG:"Bulgaria",MD:"Moldova",GE:"Georgia",AM:"Armenia",AZ:"Azerbaijan",UZ:"Uzbekistan"};

async function init() {
  bindCopy();
  var data = null;
  try {
    var r = await fetch("data.json", { cache: "no-store" });
    if (r.ok) {
      data = await r.json();
    }
  } catch (e) {
    data = null;
  }
  if (!data) {
    setText("updated", "after the first hourly run");
    return;
  }
  setText("updated", data.updated || "unknown");
  setText("fullprobe", data.full_probe ? "yes" : "tcp only");
  setText("alive", data.alive || 0);
  setText("elite", data.elite || 0);
  setText("best", data.best || 0);
  setText("gaming", data.gaming || 0);
  setText("countries", data.countries || 0);
  setText("mtcp", data.median_tcp_ms || 0);
  setText("mhttp", data.median_http_ms || 0);
  setText("totalin", data.total_in || 0);
  setText("parsed", data.parsed || 0);
  setText("sources", String(data.sources_ok || 0) + " of " + String(data.sources_total || 0));
  var counts = data.country_counts || {};
  var rows = Object.keys(counts).map(function (k) { return [k, counts[k]]; });
  rows.sort(function (a, b) { return b[1] - a[1]; });
  var tb = document.getElementById("ctable");
  if (!tb) {
    return;
  }
  tb.textContent = "";
  for (var i = 0; i < rows.length; i++) {
    var cc = rows[i][0];
    var n = rows[i][1];
    var tr = document.createElement("tr");
    var td1 = document.createElement("td");
    td1.textContent = NAMES[cc] || cc;
    var td2 = document.createElement("td");
    td2.textContent = n;
    var td3 = document.createElement("td");
    var file = "output" + "/" + "countries" + "/" + cc + ".txt";
    td3.textContent = file + " ";
    var b = document.createElement("button");
    b.textContent = "Copy link";
    (function (code, btn) {
      btn.addEventListener("click", function () {
        var url = "https:" + "/" + "/raw.githubusercontent.com/lumskyy/LumoVessConfig/main/output/countries/" + code + ".txt";
        copyText(url);
        btn.textContent = "Copied";
        setTimeout(function () { btn.textContent = "Copy link"; }, 1200);
      });
    })(cc, b);
    td3.appendChild(b);
    tr.appendChild(td1);
    tr.appendChild(td2);
    tr.appendChild(td3);
    tb.appendChild(tr);
  }
}

document.addEventListener("DOMContentLoaded", init);
