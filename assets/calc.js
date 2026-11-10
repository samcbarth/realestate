/* Deal Math calculators. Pure math lives in CALCS so build.py can run the
   same functions in Node to fill the worked examples on each page. */
(function (root) {
  'use strict';

  function payment(principal, annualRatePct, years) {
    var n = years * 12;
    var r = annualRatePct / 100 / 12;
    if (principal <= 0 || n <= 0) return 0;
    if (r === 0) return principal / n;
    return principal * r / (1 - Math.pow(1 + r, -n));
  }

  var CALCS = {
    mortgage: function (i) {
      var down = i.price * i.down_pct / 100;
      var loan = Math.max(0, i.price - down);
      var pi = payment(loan, i.rate, i.years);
      var pmi = i.down_pct < 20 ? loan * i.pmi_pct / 100 / 12 : 0;
      var tax = i.tax_yr / 12, ins = i.ins_yr / 12;
      return {
        down: down, loan: loan, pi: pi, tax_mo: tax, ins_mo: ins, pmi_mo: pmi,
        hoa_mo: i.hoa_mo, total: pi + tax + ins + pmi + i.hoa_mo,
        total_interest: pi * i.years * 12 - loan
      };
    },

    rental: function (i) {
      var down = i.price * i.down_pct / 100;
      var loan = i.price - down;
      var debt = payment(loan, i.rate, i.years);
      var gross = (i.rent + i.other_income) * 12;
      var vacancy = gross * i.vacancy / 100;
      var egi = gross - vacancy;
      var pctCosts = i.rent * 12 * (i.maint + i.mgmt + i.capex) / 100;
      var opex = i.tax_yr + i.ins_yr + (i.hoa_mo + i.utilities_mo) * 12 + pctCosts;
      var noi = egi - opex;
      var cfYr = noi - debt * 12;
      var cash = down + i.closing;
      return {
        gross: gross, egi: egi, opex: opex, noi: noi,
        cap_rate: i.price > 0 ? noi / i.price * 100 : 0,
        debt_mo: debt, cashflow_mo: cfYr / 12, cashflow_yr: cfYr,
        cash_in: cash, coc: cash > 0 ? cfYr / cash * 100 : null,
        dscr: debt > 0 ? noi / (debt * 12) : null
      };
    },

    yield: function (i) {
      var annual = i.rent * 12;
      var net = annual - i.expenses_yr;
      var basis = i.price + i.costs;
      return {
        annual_rent: annual, net_income: net,
        gross_yield: i.price > 0 ? annual / i.price * 100 : 0,
        net_yield: basis > 0 ? net / basis * 100 : 0
      };
    },

    flip: function (i) {
      var rehabTotal = i.rehab * (1 + i.contingency / 100);
      var buyClosing = i.purchase * i.buy_closing_pct / 100;
      var holding = i.holding_mo * i.months;
      var loan = (i.purchase + rehabTotal) * i.loan_pct / 100;
      var interest = loan * i.rate / 100 / 12 * i.months;
      var points = loan * i.points / 100;
      var sellCosts = i.arv * i.sell_cost_pct / 100;
      var total = i.purchase + buyClosing + rehabTotal + holding + interest + points + sellCosts;
      var profit = i.arv - total;
      var cash = i.purchase + buyClosing + rehabTotal + holding + interest + points - loan;
      var roi = cash > 0 ? profit / cash * 100 : null;
      return {
        rehab_total: rehabTotal, buy_closing: buyClosing, holding: holding,
        loan: loan, interest: interest, points_cost: points, sell_costs: sellCosts,
        total_cost: total, profit: profit, cash_needed: cash, roi: roi,
        annualized: roi === null || i.months <= 0 ? null : roi * 12 / i.months
      };
    },

    brrrr: function (i) {
      var allIn = i.purchase + i.closing + i.rehab + i.holding;
      var refiLoan = i.arv * i.refi_ltv / 100;
      var cashBack = refiLoan - i.refi_cost;
      var left = allIn - cashBack;
      var pmt = payment(refiLoan, i.rate, i.years);
      var noi = i.rent * (1 - i.opex_pct / 100);
      var cf = noi - pmt;
      return {
        all_in: allIn, refi_loan: refiLoan, cash_back: cashBack,
        cash_left: left, payment: pmt, noi_mo: noi, cashflow_mo: cf,
        equity: i.arv - refiLoan,
        coc: left > 0 ? cf * 12 / left * 100 : null
      };
    },

    rule70: function (i) {
      var capped = i.arv * i.pct / 100;
      return { arv_pct: capped, max_offer: capped - i.repairs };
    },

    wholesale: function (i) {
      var buyerMax = i.arv * i.investor_pct / 100 - i.repairs;
      var fee = buyerMax - i.contract_price;
      return { buyer_max: buyerMax, max_fee: fee, net_fee: fee - i.costs };
    },

    proptax_tx: function (i) {
      var schoolEx = i.homestead ? 140000 + (i.over65 ? 60000 : 0) : 0;
      var localEx = i.homestead ? i.value * i.local_pct / 100 : 0;
      var schoolTaxable = Math.max(0, i.value - schoolEx);
      var otherTaxable = Math.max(0, i.value - localEx);
      var school = schoolTaxable * i.school_rate / 100;
      var other = otherTaxable * (i.county_rate + i.city_rate + i.other_rate) / 100;
      var total = school + other;
      return {
        school_taxable: schoolTaxable, other_taxable: otherTaxable,
        school_tax: school, other_tax: other, total: total, monthly: total / 12,
        effective: i.value > 0 ? total / i.value * 100 : 0
      };
    },

    proptax_ok: function (i) {
      var assessed = i.value * i.ratio / 100;
      var net = Math.max(0, assessed - (i.homestead ? 1000 : 0));
      var total = net * i.mills / 1000;
      return {
        assessed: assessed, net_assessed: net, total: total, monthly: total / 12,
        effective: i.value > 0 ? total / i.value * 100 : 0
      };
    }
  };

  function fmt(v, kind) {
    if (v === null || v === undefined || !isFinite(v)) {
      return kind === 'pct' ? 'n/a (no cash left in the deal)' : 'n/a';
    }
    if (kind === 'money') {
      var s = Math.abs(v).toLocaleString('en-US', { maximumFractionDigits: 0 });
      return (v < 0 ? '-$' : '$') + s;
    }
    if (kind === 'money2') {
      return (v < 0 ? '-$' : '$') + Math.abs(v).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }
    if (kind === 'pct') return v.toFixed(2) + '%';
    if (kind === 'ratio') return v.toFixed(2);
    return String(Math.round(v));
  }

  var api = { CALCS: CALCS, fmt: fmt, payment: payment };
  if (typeof module !== 'undefined' && module.exports) { module.exports = api; return; }
  root.DealMath = api;

  function readForm(form) {
    var data = {};
    Array.prototype.forEach.call(form.elements, function (el) {
      if (!el.name) return;
      if (el.type === 'checkbox') data[el.name] = el.checked;
      else data[el.name] = parseFloat(el.value) || 0;
    });
    return data;
  }

  function run(form) {
    var fn = CALCS[form.getAttribute('data-calc')];
    if (!fn) return;
    var out = fn(readForm(form));
    var box = document.getElementById(form.getAttribute('data-results'));
    if (!box) return;
    Array.prototype.forEach.call(box.querySelectorAll('[data-out]'), function (el) {
      var key = el.getAttribute('data-out');
      var v = out[key];
      el.textContent = fmt(v, el.getAttribute('data-fmt'));
      var row = el.closest('.result');
      if (row) row.classList.toggle('neg', typeof v === 'number' && v < 0 && el.getAttribute('data-fmt') !== 'ratio');
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    Array.prototype.forEach.call(document.querySelectorAll('form[data-calc]'), function (form) {
      form.addEventListener('input', function () { run(form); });
      form.addEventListener('change', function () { run(form); });
      form.addEventListener('submit', function (e) { e.preventDefault(); run(form); });
      form.addEventListener('reset', function () { setTimeout(function () { run(form); }, 0); });
      run(form);
    });
  });
})(typeof window !== 'undefined' ? window : this);
