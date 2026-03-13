/* Minification failed. Returning unminified contents.
(38,19-20): run-time error JS1014: Invalid character: `
(38,28-36): run-time error JS1193: Expected ',' or ')': inválida
(38,67-68): run-time error JS1193: Expected ',' or ')': o
(38,154-159): run-time error JS1193: Expected ',' or ')': valor
(38,209-217): run-time error JS1193: Expected ',' or ')': qualquer
(38,238-239): run-time error JS1014: Invalid character: `
(38,239-240): run-time error JS1010: Expected identifier: )
(41,9-10): run-time error JS1002: Syntax error: }
(45,13-14): run-time error JS1195: Expected expression: )
(45,15-16): run-time error JS1004: Expected ';': {
(82,2-3): run-time error JS1195: Expected expression: )
(84,31-32): run-time error JS1004: Expected ';': {
(1742,17-18): run-time error JS1195: Expected expression: )
(1742,20-21): run-time error JS1195: Expected expression: >
(1742,49-50): run-time error JS1004: Expected ';': )
(1854,12-13): run-time error JS1014: Invalid character: `
(1854,14-15): run-time error JS1004: Expected ';': {
(1854,17-18): run-time error JS1014: Invalid character: `
(1856,7-15): run-time error JS1004: Expected ';': function
(1857,26-27): run-time error JS1004: Expected ';': $
(1866,7-15): run-time error JS1004: Expected ';': function
(1868,21-29): run-time error JS1004: Expected ';': doIAAjax
(1874,7-15): run-time error JS1004: Expected ';': function
(1875,22-27): run-time error JS1004: Expected ';': getIA
(1911,7-15): run-time error JS1004: Expected ';': function
(1925,7-15): run-time error JS1004: Expected ';': function
(1926,26-31): run-time error JS1004: Expected ';': getIA
(2757,1-2): run-time error JS1107: Expecting more source characters
(1849,1-27): run-time error JS1301: End of file encountered before function is properly closed: function getStringValue(x)
(40,13-25): run-time error JS1018: 'return' statement outside of function: return false
 */
var ArrayMeses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro", "Décimo Terceiro"];

// Relato 4841431 - [WEB PRODUÇÃO] Erro de ticket ao tentar retificar CPF de dependente do evento S-2400
function decodeHtml(html) {
    var txt = document.createElement("textarea");
    txt.innerHTML = html;
    return txt.value;
}

// Tratamento do "ajaxStatus" da aplicação
$(document).on("ajaxStart submit", function () {
    // Relato 4841431 - [WEB PRODUÇÃO] Erro de ticket ao tentar retificar CPF de dependente do evento S-2400
    // Antes de qualquer submissão (ajax ou não-ajax), decodificar os valores presentes nos campos de entrada para
    // evitar o problema de não recebimento por parte do framework
    $('[value]').each(function () {
        $(this).val(decodeHtml($(this).val()));
    });

    $('#loading').show();
});

$(document).on("ajaxStop", function () {
    $('#loading').hide();
});

// Tratamento dado a todo formulário submetido que possa conter caracteres que façam o framework reconhecer
// strings potencialmente perigosas
// Exemplo de erro dessa natureza:
// A potentially dangerous Request.Form value was detected from the client (EventoAdmissao.EnderecoResidencialBR.DescricaoLogradouro="<SEM ENDERECO>").
$(document).on('submit', 'form', function () {
    const elementosSubmetidos = $(this).find('input, select, textarea');

    for (let i = 0; i < elementosSubmetidos.length; i++) {
        const elemento = $(elementosSubmetidos[i]);
        const valorElemento = elemento.val();

        if (/(<|&lt;|&#60;)\S+/.test(valorElemento) && elemento.is(':visible')) {
            alert(`Entrada inválida submetida! Por favor, corrija o campo com valor "${decodeHtml(valorElemento)}" antes de prosseguir com a operação (o valor não pode conter "<*" em sua composição, onde * é qualquer caracter não-vazio).`);
            $('#loading').hide();
            return false;
        }
    }
});

$(function () {
    // Ajaxstatus ativado quando se clica em algum item de menu ou âncora que cause redirecionamento
    $('.nav.navbar-nav a:not(.dropdown-toggle), a:not(.nofireajaxstatus)[onclick*="location"]').click(function () {
        $('#loading').show();
    });

    // Classe a ser utilizada em inputs quando não se quer utilizar a validação do jquery (data-val-ignore)
    var formularios = $("form");

    if (formularios.length > 0) {
        formularios.data("validator").settings.ignore = $("form").data("validator").settings.ignore + ", .data-val-ignore";
    }

    if ($("#dialog-mensagem-sucesso").length > 0) {
        $("#dialog-mensagem-sucesso").dialog(
            {
                appendTo: 'body',
                position: ['center', 200],
                dialogClass: 'modal',
                draggable: false,
                resizable: false,
                width: 700,
                title: 'Sucesso',
                modal: true, open: function () { $(".ui-dialog").scrollTop("0"); },
                buttons: [
                    {
                        text: "Ok",
                        "class": 'btn btn-primary',
                        click: function () {
                            $(this).dialog("close");
                        }
                    }
                ],
            });
    }

    direcionarTelaPara();
});

function direcionarTelaPara() {
    var seletorDirecionarPara = $('#DirecionarPara');

    if (seletorDirecionarPara.length > 0 && seletorDirecionarPara.val() != '' && $(seletorDirecionarPara.val()).length > 0) {
        /*$('html, body').animate({
            scrollTop: $(seletorDirecionarPara.val()).offset().top
        }, 1000);*/
        window.location.href = seletorDirecionarPara.val();
    }
}

// Método customizado de validação de campo de número de recibo do eSocial
jQuery.validator.addMethod("recibo-esocial-pattern", function (value, element) {
    $(element).siblings(".field-validation-error").html("");
    value = jQuery.trim(value);
    return this.optional(element) || /^[1]{1}\.\d{1}\.\d{19}$/.test(value);
}, "Formato inválido: o campo deve ter o formato N.N.NNNNNNNNNNNNNNNNNNN (ex: 1.1.0000000000123456789).");

// Método customizado de validação do campo de número de contrato de empréstimo
jQuery.validator.addMethod("nrdoc-pattern", function (value, element) {
    $(element).siblings(".field-validation-error").html("");
    value = jQuery.trim(value);
    return this.optional(element) || /^[A-Za-z0-9][-_A-Za-z0-9/.//]{0,13}[A-Za-z0-9]$/.test(value);
}, "Formato inválido: o campo deve começar e terminar com um caractere alfanumérico e pode conter até 15 caracteres, incluindo letras, números, barras, hífens, pontos e subtraços.");

// Método customizado de validação de valores positivos
jQuery.validator.addMethod("valor-positivo", function (value, element) {
    $(element).siblings('.field-validation-error').html('');
    value = jQuery.trim(value);
    return this.optional(element) || (value != '' && parseFloat(value.replace('.', '').replace(',', '.')) != 0);
}, "O valor informado deverá ser maior que ZERO.");

// Método customizado de validação de campos "mês/ano" (MM/yyyy) aplicado aos elementos com classe DP
jQuery.validator.addMethod("DP", function (value, element) {
    $(element).siblings('.field-validation-error').html('');
    value = jQuery.trim(value);
    return this.optional(element) || (value != '' && validaData1(value));
}, "Data inválida.");

//xxxxxxx data 2000
jQuery.validator.addMethod("DP2000", function (value, element) {
    $(element).siblings('.field-validation-error').html('');
    value = jQuery.trim(value);
    return this.optional(element) || (value != '' && validaData3(value));
}, "Ano deve ser maior ou igual a 2000.");

// Método customizado de validação de campos "dia/mês/ano" (dd/MM/yyyy) aplicado aos elementos com classe D
jQuery.validator.addMethod("D", function (value, element) {
    $(element).siblings('.field-validation-error').html('');
    value = jQuery.trim(value);
    return this.optional(element) || (value != '' && validaData2(value));
}, "Data inválida.");

// Método customizado de validação de campos "horas:minutos" (hh:mm) aplicado aos elementos com classe horario
jQuery.validator.addMethod("horario", function (value, element) {
    $(element).siblings('.field-validation-error').html('');
    value = jQuery.trim(value);
    return this.optional(element) || (value != '' && validaHorario(value));
}, "Horário inválido.");

// Método customizado de validação de campos "período apuração" (99/9999) aplicado aos elementos com classe perApuracao
jQuery.validator.addMethod("perApuracao", function (value, element) {
    $(element).siblings('.field-validation-error').html('');
    value = jQuery.trim(value);
    return this.optional(element) || (value != '' && validaPerApuracao(value));
}, "Período de Apuração inválido.");

// Método customizado de validação de campos "cnpj" (00.000.000/0000-00) aplicado aos elementos com classe cnpj
jQuery.validator.addMethod("cnpj", function (value, element) {
    $(element).siblings('.field-validation-error').html('');
    value = jQuery.trim(value);
    return this.optional(element) || (value != '' && validaCnpj(value));
}, "CNPJ inválido.");

jQuery.validator.addMethod("cpf", function (value, element) {
    $(element).siblings('.field-validation-error').html('');
    value = jQuery.trim(value);

    return this.optional(element) || (value != '' && validaCPF(value));
}, "CPF inválido.");

jQuery.validator.addMethod("caepf", function (value, element) {
    $(element).siblings('.field-validation-error').html('');
    value = jQuery.trim(value);

    return this.optional(element) || (value != '' && validaCAEPF(value));
}, "CAEPF inválido.");

jQuery.validator.addMethod("cno", function (value, element) {
    $(element).siblings('.field-validation-error').html('');
    value = jQuery.trim(value);

    return this.optional(element) || (value != '' && validaCNO(value));
}, "CNO inválido.");

jQuery.validator.addMethod("numeroJornada", function (value, element) {
    $(element).siblings('.field-validation-error').html('');
    value = jQuery.trim(value);
    return this.optional(element) || (value != '' && VMasker.toPattern(value, "9999"));
}, "O campo permite somente números.");

jQuery.validator.addMethod("CEP", function (value, element) {
    $(element).siblings('.field-validation-error').html('');
    value = jQuery.trim(value);

    return this.optional(element) || (value != '' && validaCEP(value));
}, "CEP inválido.");

// Validação complementar para campos obrigatórios (required) que só os considera válidos se forem diferentes de nulo e vazio
jQuery.validator.addMethod("required", function (value, element) {
    //$(element).siblings('.field-validation-error').html('');

    return value != null && jQuery.trim(value) != '';
}, "Campo de preenchimento obrigatório.");

// Validação customizada para email
jQuery.validator.addMethod("email", function (value, element) {
    $(element).siblings('.field-validation-error').html('');
    value = jQuery.trim(value);

    return this.optional(element) || (value != '' && validaEmail(value));
}, "Email inválido.");

$.validator.methods.maiorQue = function (value, element, param) {
    return this.optional(element) || validaValorMaiorQue(value, param);
}

$.validator.messages.maiorQue = $.validator.format("O valor deve ser maior que {0}.");

function validaValorMaiorQue(valor, parametro) {
    return (valor.ReplaceAll('.', '').ReplaceAll(',', '.') * 1) > (parametro.ReplaceAll('.', '').ReplaceAll(',', '.') * 1);
}

$.validator.methods.menorOuIgual = function (value, element, param) {
    return this.optional(element) || validaValorMenorOuIgual(value, param);
}

$.validator.messages.menorOuIgual = $.validator.format("O valor deve ser menor ou igual a {0}.");

function validaValorMenorOuIgual(valor, parametro) {
    return (valor.ReplaceAll('.', '').ReplaceAll(',', '.') * 1) <= (parametro.ReplaceAll('.', '').ReplaceAll(',', '.') * 1);
}

$.validator.methods.max = function (value, element, param) {
    var valor = value.replace(",", ".") * 1;

    return this.optional(element) || (valor != 'NaN' && valor <= param);
}

$.validator.methods.min = function (value, element, param) {
    var valor = value.replace(",", ".") * 1;

    return this.optional(element) || (valor != 'NaN' && valor >= param);
}

$(document).ready(function () {

    $('.table').has('thead').not(".sem-paginacao, .table-ordenada").each(function () {
        if (!$.fn.DataTable.isDataTable($(this))) {
            $(this).dataTable({
                "bPaginate": $(this).hasClass('table-paginada'),
                "bLengthChange": false,
                "bFilter": false,
                "bSort": false,
                "bInfo": false,
                "bAutoWidth": false,
                "sPaginationType": "full_numbers",
                "iDisplayLength": $(this).attr("DisplayLength") == 'undefined' ? 10 : $(this).attr("DisplayLength"),
                "oLanguage": {
                    "sEmptyTable": "Nenhum registro encontrado."
                },
                "fnDrawCallback": function (oSettings) {
                    if (oSettings._iDisplayLength > oSettings.fnRecordsDisplay()) {
                        $(oSettings.nTableWrapper).find('.dataTables_paginate').hide();
                    }
                    $('.first,.previous,.next,.last').html('');
                }
            });
        }
    });
    $(".download").html("Baixar XML </i>");
    $(".downloadMovimentacoes").html("<i class='fa fa-arrow-alt-circle-down' style='color:#7b7b75'></i>");
    //Filtrar Municipio ao selecionar estado
    $(".filtroEstado").change(function () {
        FiltrarMunicipios($(this).val(), $(this).parent('div').parent('div').next().find('.municipioFiltrado').attr("id"), null);
    });

    $('.municipioFiltrado').each(function () {
        municipioCarregado = $(this).val();
        if (municipioCarregado != undefined) {
            FiltrarMunicipios($(this).parent('div').parent('div').prev().find('.filtroEstado').val(), $(this).attr("id"), municipioCarregado);
        }
    });

    var icons = {
        header: "iconClosed",    // custom icon class
        activeHeader: "iconOpen" // custom icon class
    };

    $('.accordion').each(function () {
        var activeAttr = parseInt($(this).attr('active'));

        activeAttr = (typeof activeAttr === "number") ? activeAttr : false;

        $(this).accordion({
            collapsible: true,
            header: ">h2",
            active: activeAttr,
            icons: icons,
            heightStyle: "content",
        });
    });

    if ($('#accordionPaginator').length > 0) {
        var paginacao = $(".accordion.principal").attr("paginacao");

        if (paginacao == null) {
            paginacao = 300
        }

        paginatorHandle = $(".accordion.principal").paginateAccordion({
            "currentPage": 0,
            "itemsPerPage": paginacao,
            "paginatorControl": $("#accordionPaginator")
        });

        // initial paginate call
        paginatorHandle.paginate();

        $("#accordionPaginator .nextPage").click(function () {
            paginatorHandle.nextPage();
        });

        $("#accordionPaginator .previousPage").click(function () {
            paginatorHandle.previousPage();
        });

        $("#accordionPaginator .goToPage").change(function () {
            var pageIndex = parseInt($(this).val(), 10);
            paginatorHandle.goToPage(pageIndex);
        });
    }

    $('select[placeholder] option[value=""]').addClass("text-muted");

    if ($('#inApp').length > 0) {
        ConfigurarVisualizacaoNoApp();
    }

});

function ConfigurarVisualizacaoNoApp() {
    $('#header').remove();
    $('footer').remove();
    $('.btn-toggle-menu').remove();
    $('.navbar').remove();
    $('#barra-brasil').remove();
    $('.btn.admissao.btn-cancelar').click(function () {
        window.location = MontaCaminhoCompleto("/Admissao/DadosIniciaisDomestico/Index?inApp=true")
    });
    //$('.btn.admissao.btn-cancelar.inApp').removeClass('hide');
}

function AbrirModalInformeRendimentos() {
    $("#dialog-informe-rendimentos").dialog(
        {
            appendTo: 'body',
            position: ['center', 50],
            dialogClass: 'modalOk modal',
            draggable: false,
            resizable: false,
            width: 700,
            title: 'Aviso',
            modal: true, open: function () { $(".ui-dialog").scrollTop("0"); },
            buttons:
                [{
                    text: "Ok",
                    "class": 'btn btn-primary',
                    click: function () {
                        $(this).dialog("close");
                    }
                }]
        });

    $('#loading').hide();
}

function redirecionar(url, exibirAjaxstatus) {
    if (typeof exibirAjaxstatus == 'undefined' || exibirAjaxstatus === undefined && exibirAjaxstatus) {
        $('#loading').show();
    }

    window.location = MontaCaminhoCompleto(url);
    return false;
}

function voltarBrowser() {
    $('#loading').show();
    history.back();
    return false;
}

function FiltrarMunicipios(siglaUf, idCampoMunicipio, codigoMunicipio) {
    campoMunicipio = $("#" + idCampoMunicipio);
    campoMunicipio.empty();
    campoMunicipio.append('<option value=""></option>');

    if (campoMunicipio.is('[readonly]') || campoMunicipio.is('[disabled]')) {
        if (codigoMunicipio != null && codigoMunicipio > 0) {
            var parametros = { 'codMunicipio': codigoMunicipio, 'idCampoMunicipio': idCampoMunicipio }
            AjaxCall(RetornoObterMunicipio, "Util/ObterMunicipio/", parametros, "Erro ao filtrar municípios.", null);
        }
    } else if (siglaUf.length > 0) {
        var parametros = { 'siglaUf': siglaUf, 'idCampoMunicipio': idCampoMunicipio, 'codMunicipioSelecionado': codigoMunicipio };
        AjaxCall(RetornoFiltrarMunicipio, "Util/FiltrarMunicipio/", parametros, "Erro ao filtrar municípios.", null);
    }
    else {
        if (codigoMunicipio != null && codigoMunicipio > 0) {
            var parametros = { 'codMunicipio': codigoMunicipio, 'idCampoMunicipio': idCampoMunicipio }
            AjaxCall(RetornoObterMunicipio, "Util/ObterMunicipio/", parametros, "Erro ao filtrar municípios.", null);
        }
    }
}

function RetornoObterMunicipio(data) {
    if (data != null && data.Sucesso) {
        campoMunicipio = $("#" + data.Objeto["IdCampoMunicipio"]);
        campoMunicipio.append('<option value=' + data.Objeto["CodigoMunicipio"] + ' title="' + data.Objeto["NomeMunicipio"] + '">' + data.Objeto["NomeMunicipio"] + '</option>');
        campoMunicipio.val(data.Objeto["CodigoMunicipio"]);
    }
}
function RetornoFiltrarMunicipio(data) {
    if (data != null && data.Objeto.length > 0) {
        if (data.Objeto[0].Key == "IdCampoMunicipio") {
            var inicio = 1;
            campoMunicipio = $("#" + data.Objeto[0].Value);
            var codigoMunicipio = "";

            if (data.Objeto[1].Key == "CodigoMunicipioSelecionado") {
                codigoMunicipio = data.Objeto[1].Value;
                inicio = 2;
            }
            for (var i = inicio; i < data.Objeto.length; ++i) {
                campoMunicipio.append('<option value=' + data.Objeto[i].Key + ' title="' + data.Objeto[i].Value + '">' + data.Objeto[i].Value + '</option>');
            }
            campoMunicipio.val(codigoMunicipio);
        }
    }
}

function AlterarTamanhoPagina(tamanho) {
    var t = $('.table').has('thead').not(".sem-paginacao").dataTable();

    //Lifted more or less right out of the DataTables source
    var oSettings = t.fnSettings();

    oSettings._iDisplayLength = parseInt(tamanho, 10);
    t._fnCalculateEnd(oSettings);

    /* If we have space to show extra rows (backing up from the end point - then do so */
    if (oSettings.fnDisplayEnd() == oSettings.fnRecordsDisplay()) {
        oSettings._iDisplayStart = oSettings.fnDisplayEnd() - oSettings._iDisplayLength;
        if (oSettings._iDisplayStart < 0) {
            oSettings._iDisplayStart = 0;
        }
    }

    if (oSettings._iDisplayLength == -1) {
        oSettings._iDisplayStart = 0;
    }

    if (oSettings._iDisplayLength <= oSettings.fnRecordsDisplay()) {
        $(oSettings.nTableWrapper).find('.dataTables_paginate').show();
    }

    t.fnDraw(oSettings);

    return t;
}

function AbrirModal(id, width, width_px) {
    //var modalWidth = !width ? (!width_px ? $(window).width() * 0.7 : width_px) : $(window).width() * (width / 100);

    $(id).modal('show').css({
        //'width': modalWidth,
        //'margin-left': -(modalWidth / 2),
        //'top': 100 + window.pageYOffset
        //'margin-top': function () { return $(this).height() >= $(window).height() ? window.pageYOffset + $(window).height() * 0.05 : window.pageYOffset - ($(this).height() / 2); }
    });
}

function FecharModal(id) {
    $(id).modal('hide');

    if ($('.modal-backdrop').hasClass('in')) {
        $('.modal-backdrop').remove();
    }
}

function AbrirJanela(id) {
    AbrirModal('#' + id);
}

function FecharJanela(id) {
    FecharModal('#' + id);
}

function MostrarMensagem(fonte, tipo, valor, classAdicional) {
    if (classAdicional == null || classAdicional == undefined) {
        classAdicional = "";
    }

    var blocoMensagem = $("#mensagem" + fonte);
    var mensagemAnterior = "";
    var classeAdicionalMensAnterior = "";

    if (blocoMensagem.find("div.alert-" + tipo).length > 0) {
        blocoMensagem.find("div.alert-" + tipo).each(function () {
            if ($(this).children("span") != null && $(this).children("span").html() != null) {
                var msg = $(this).children("span").html().trim();
                if (mensagemAnterior.length > 0 && msg.length > 0) {
                    mensagemAnterior += "<br/>";
                }
                mensagemAnterior += msg;
                var classeAd = $(this).attr('class').replace("fade-alert alert alert-" + tipo, "").trim();

                if (classeAdicionalMensAnterior.indexOf(classeAd) < 0) {
                    classeAdicionalMensAnterior += " " + classeAd;
                }
            }
        });

        blocoMensagem.find("div.alert-" + tipo).remove();
    }

    var $divMensagem = $("<div>", { "class": "fade-alert alert alert-" + tipo + " " + classAdicional + " " + classeAdicionalMensAnterior });
    $divMensagem.append("<a class='close' onclick='$(this).parent().slideUp(1000, function(){ $(this).children().remove(); })'>&times;</a><span>" + mensagemAnterior + "</span>").slideDown();

    if (valor == undefined || valor == null) {
        valor = "Houve um erro inesperado no retorno da execução."
    }

    if (valor.length > 1 && typeof valor != "string") {
        var listaStr = (mensagemAnterior.length > 0 ? "<br/>" : "") + "<ul></ul>";
        for (var i = 0; i < valor.length; i++) {
            listaStr += '<li>' + valor[i] + '</li>';
        }
        $divMensagem.find("span").append(listaStr);
    }
    else {
        $divMensagem.find("span").append((mensagemAnterior.length > 0 ? "<br/>" : "") + valor);
    }

    blocoMensagem.append($divMensagem);

    if (tipo == "success") {
        timeoutID = window.setTimeout(function () {
            blocoMensagem.slideUp(1000, function () { $(this).children().remove(); });
        }, 10000);
    } /*else if (tipo == "warning") {
        timeoutID = window.setTimeout(function () {
            blocoMensagem.slideUp(1000, function () { $(this).children().remove(); });
        }, 10000);
    }*/ else if (typeof timeoutID != 'undefined' && timeoutID !== undefined) {
        window.clearTimeout(timeoutID);
    }

    if (!$("#mensagem" + fonte).is(":visible")) {
        $("#mensagem" + fonte).show();
    }
    $.scrollTo("#mensagem" + fonte, 400, { offset: -30 });

    // Retorno da referência do bloco que contém as mensagens para posteriores utilizações
    return blocoMensagem;
}

function MostrarMensagemOriginal(fonte, tipo, valor, classAdicional) {
    if (classAdicional == null || classAdicional == undefined) {
        classAdicional = "";
    }

    var blocoMensagem = $("#mensagem" + fonte);

    blocoMensagem.html("<div class='fade-alert alert alert-" + tipo + " " + classAdicional + "'><a class='close' onclick='$(this).parent().slideUp(1000, function(){ $(this).children().remove(); })'>&times;</a><span></span></div>").slideDown();

    if (valor == undefined || valor == null) {
        valor = "Houve um erro inesperado no retorno da execução."
    }
    if (valor.length > 1 && typeof valor != "string") {
        blocoMensagem.find("span").append('<ul></ul>');

        for (var i = 0; i < valor.length; i++) {
            blocoMensagem.find("ul").append('<li>' + valor[i] + '</li>');
        }
    }
    else {
        blocoMensagem.find("span").html(valor);
    }

    if (tipo == "success") {
        timeoutID = window.setTimeout(function () {
            blocoMensagem.slideUp(1000, function () { $(this).children().remove(); });
        }, 10000);
    } /*else if (tipo == "warning") {
        timeoutID = window.setTimeout(function () {
            blocoMensagem.slideUp(1000, function () { $(this).children().remove(); });
        }, 10000);
    }*/ else if (typeof timeoutID != 'undefined' && timeoutID !== undefined) {
        window.clearTimeout(timeoutID);
    }

    $.scrollTo("#mensagem" + fonte, 400, { offset: -30 });

    // Retorno da referência do bloco que contém as mensagens para posteriores utilizações
    return blocoMensagem;
}

function ConfigurarToolTips() {
    $('.btn-tooltip').tooltip('destroy').tooltip({ placement: 'top' });
    //$('.btn-popover').popover();

    ConfigurarHelpLabels();
}
function ConfigurarHelpLabels() {
    $('[data-help]').each(function () {
        $(this).children('.icon-ajuda').popover('destroy').remove();
        $(this).append('<i class="icon-ajuda"></i>');
        CriarPopover($(this).children('i'), $(this).attr('data-titulo'), $(this).attr('data-help'), 'right', 'hover');
    });
}

function CriarPopover(el, titulo, texto, pos, evento, aberto, ajuda) {
    if (!evento) evento = 'manual';

    el.popover({ title: titulo, content: texto, placement: pos, trigger: evento });
    if (aberto) el.click(function () { $(this).popover('close'); }).popover('show');
    //if (ajuda) $(el).addClass('ajuda-popover');
}

//function IniciaTimerSessao() {
//    var timeoutMinutos = 20;

//    var timeoutSegundos = timeoutMinutos * 60;
//    var duration = moment.duration(timeoutSegundos, 'seconds');
//    var interval = 1000;

//    window.idIntervalo = setInterval(function () {
//        if (duration.asSeconds() <= 0) {
//            clearInterval(window.idIntervalo);
//            $('.countdown').text("Sessão expirada");

//            $("#dialog-sessao-expirou").dialog(
//            {
//                appendTo: 'body',
//                position: ['center', 50],
//                dialogClass: 'modal',
//                draggable: false,
//                resizable: false,
//                width: 600,
//                title: 'Sessão expirada',
//                modal: true, open: function () { $(".ui-dialog").scrollTop("0"); },
//                buttons: [
//                    {
//                        text: "Continuar",
//                        "id": 'btnContinuarAdiantamento',
//                        "class": 'btn btn-primary',
//                        click: function () {
//                            location.reload();
//                        }
//                    }]
//            });
//        }
//        else {
//            duration = moment.duration(duration.asSeconds() - 1, 'seconds');
//            var text = (duration.hours() > 0) ? (duration.hours() < 10) ? '0' + duration.hours() + ':' : duration.hours() + ':' : '';
//            text += (duration.minutes() > 0) ? (duration.minutes() < 10) ? '0' + duration.minutes() + ':' : duration.minutes() + ':' : '00:';
//            text += (duration.seconds() > 0) ? (duration.seconds() < 10) ? '0' + duration.seconds() : duration.seconds() : '00';
//            $('.countdown').text(text);
//            $('.countdown').fadeIn('slow');
//        }
//    }, interval);
//}

// Valida data no formato MM/aaaa
function validaData1(strData) {
    var filter = new RegExp("(0[123456789]|10|11|12)([/])(19[0-9][0-9]|2[0-9][0-9][0-9])");
    return filter.test(strData);
}

// Valida data no formato dd/MM/aaaa
function validaData2(strData) {
    var filter = new RegExp("(0[123456789]|[12][0123456789]|30|31)([/])(0[123456789]|10|11|12)([/])(19[0-9][0-9]|2[0-9][0-9][0-9])");
    var eValido = filter.test(strData);

    // Validar dia e seu respectivo mês
    if (eValido) {
        var mes = parseInt(strData.substring(3, 5));

        // Mês de fevereiro
        if (mes == 2) {
            // Considerar se se trata de ano bissexto
            var ano = parseInt(strData.substring(6, 10));
            var limiteFevereiro = (((ano % 4 == 0) && (ano % 100 != 0)) || (ano % 400 == 0)) ? 30 : 29;

            eValido = parseInt(strData.substring(0, 2)) < limiteFevereiro;
        }

        // Meses restantes com 30 dias
        if (mes == 4 || mes == 6 || mes == 9 || mes == 11) {
            eValido = parseInt(strData.substring(0, 2)) < 31;
        }
    }

    return eValido;
}

// Valida data no formato MM/aaaa
function validaData3(strData) {
    var filter = new RegExp("(0[123456789]|10|11|12)([/])(19[0-9][0-9]|2[0-9][0-9][0-9])");
    var eValido = filter.test(strData);

    // Validar dia e seu respectivo mês
    if (eValido) {
        var ano = parseInt(strData.substring(3, 7));

        eValido = (ano >= 2000);
    }

    return eValido;
}

// Valida horário no formato hh:mm
function validaHorario(strData) {
    var filter = new RegExp("([01][0-9]|2[0123])([:])([012345][0-9])");
    return filter.test(strData);
}

// Valida horário no formato 99/9999 ou 9999
function validaPerApuracao(strData) {
    if (strData.indexOf('/') !== -1) {
        if (strData.substr(2, 1) == '/') {
            return true;
        }
        else {
            return false;
        }
    }
    else {
        if (strData.length != 4 && strData.length != 7) {
            return false;
        }
    }

    return true;
}

// Formata moeda no padrão brasileiro: 1.000,00
function FormatarMoeda(numero) {
    numero = numero.toFixed(2).split('.');
    // Se o número inicial for 100.00, numero[0] será 100 e numero[1] será 00
    numero[0] = numero[0].split(/(?=(?:...)*$)/).join('.');

    return numero.join(',');
}

// Valida cnpj no formato 00.000.000/0000-00
function validaCnpj(strData) {
    var filter = new RegExp("([0-9]{2}).([0-9]{3}).([0-9]{3})([/])([0-9]{4})([-])([0-9]{2})");
    return filter.test(strData) && TestaCNPJ(strData);
}

// Valida cpf 
function validaCPF(strData) {
    strData = strData.replace(/\./g, "");
    strData = strData.replace("-", '');
    var filter = new RegExp("([0-9]{11})");
    return filter.test(strData) && TestaCPF(strData);
}


// Valida CAEPF no formato NNN.NNN.NNN/NNN-NN (RNG 272534)
function validaCAEPF(strData) {
    ////var filter = new RegExp("([0-9]{13})([-])([0-9]{2})");

    var filter = new RegExp("([0-9]{3})([.])([0-9]{3})([.])([0-9]{3})([/])([0-9]{3})([-])([0-9]{2})");

    return filter.test(strData) && TestaCAEPF(strData);
}

// Valida CNO no formato 99.999.99999/99
function validaCNO(strData) {
    var filter = new RegExp("([0-9]{2})([.])([0-9]{3})([.])([0-9]{5})([/])([0-9]{2})");
    return filter.test(strData) && TestaCNO(strData);
}


// Verifica se CAEPF é válido.
function TestaCAEPF(strData) {

    strData = strData.replace(".", "").replace(".", "").replace("/", "").replace("-", "");

    var pesos = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
    var soma1 = 0;
    var soma2 = 0;
    var digito = 0;

    for (i = 0; i < pesos.length - 1; i++) {
        digito = strData.substring(i, i + 1);
        soma1 += digito * pesos[i + 1];
        soma2 += digito * pesos[i];
    }

    var resto1 = soma1 % 11;
    var dv1 = (resto1 < 2) ? 0 : 11 - resto1;

    soma2 += 2 * dv1;
    var resto2 = soma2 % 11;
    var dv2 = (resto2 < 2) ? 0 : 11 - resto2;

    return (strData.substring(strData.length - 2, strData.length)) == (parseInt(dv1 + '' + dv2) + 12) % 100;
}

// Verifica se CNO é válido.
function TestaCNO(strData) {

    strData = strData.replace(".", '').replace(".", '');
    ////strData = strData.replace(".", '');
    strData = strData.replace("/", '');

    var pesos = [7, 4, 1, 8, 5, 2, 1, 6, 3, 7, 4];
    var soma = 0;

    for (i = 0; i < 11; i++) {
        soma += strData.charAt(i) * pesos[i];
    }

    var unidade = soma % 10;
    var dezena = ((soma % 100) - unidade) / 10;
    var resto = (unidade + dezena) % 10;

    return (strData.charAt(strData.length - 1)) == ((resto == 0) ? 0 : 10 - resto);
}

//
function TestaCNPJ(cnpj) {

    cnpj = cnpj.replace(/[^\d]+/g, '');

    if (cnpj == '') return false;

    if (cnpj.length != 14)
        return false;

    // Elimina CNPJs invalidos conhecidos
    if (cnpj == "00000000000000" ||
        cnpj == "11111111111111" ||
        cnpj == "22222222222222" ||
        cnpj == "33333333333333" ||
        cnpj == "44444444444444" ||
        cnpj == "55555555555555" ||
        cnpj == "66666666666666" ||
        cnpj == "77777777777777" ||
        cnpj == "88888888888888" ||
        cnpj == "99999999999999")
        return false;

    // Valida DVs
    tamanho = cnpj.length - 2
    numeros = cnpj.substring(0, tamanho);
    digitos = cnpj.substring(tamanho);
    soma = 0;
    pos = tamanho - 7;

    for (i = tamanho; i >= 1; i--) {
        soma += numeros.charAt(tamanho - i) * pos--;
        if (pos < 2)
            pos = 9;
    }

    resultado = soma % 11 < 2 ? 0 : 11 - soma % 11;

    if (resultado != digitos.charAt(0))
        return false;

    tamanho = tamanho + 1;
    numeros = cnpj.substring(0, tamanho);
    soma = 0;
    pos = tamanho - 7;

    for (i = tamanho; i >= 1; i--) {
        soma += numeros.charAt(tamanho - i) * pos--;
        if (pos < 2)
            pos = 9;
    }

    resultado = soma % 11 < 2 ? 0 : 11 - soma % 11;

    if (resultado != digitos.charAt(1))
        return false;

    return true;
}

// Verifica se CPF é válido. Fonte: http://www.receita.fazenda.gov.br/aplicacoes/atcta/cpf/funcoes.js
function TestaCPF(strCPF) {
    var Soma;
    var Resto;
    var cpfsInvalidosConhecidos = ["00000000000", "11111111111", "22222222222", "33333333333", "44444444444", "55555555555", "66666666666", "77777777777", "88888888888", "99999999999"];
    Soma = 0;
    if (cpfsInvalidosConhecidos.indexOf(strCPF) >= 0)
        return false;
    for (i = 1; i <= 9; i++)
        Soma = Soma + parseInt(strCPF.substring(i - 1, i)) * (11 - i);
    Resto = (Soma * 10) % 11;
    if ((Resto == 10) || (Resto == 11))
        Resto = 0;
    if (Resto != parseInt(strCPF.substring(9, 10)))
        return false;
    Soma = 0;
    for (i = 1; i <= 10; i++)
        Soma = Soma + parseInt(strCPF.substring(i - 1, i)) * (12 - i);
    Resto = (Soma * 10) % 11;
    if ((Resto == 10) || (Resto == 11))
        Resto = 0;
    if (Resto != parseInt(strCPF.substring(10, 11)))
        return false;
    return true;
}

// Valida CEP no formato 00000-000
function validaCEP(strData) {
    var filter = new RegExp("([0-9]{5})([-])([0-9]{3})");
    return filter.test(strData);
}
// Valida CEP no formato  .+\@.+\..+ (mesma validação usada no AN)
function validaEmail(strData) {
    // Começar ou terminar com "@" ou "."
    if (/^@.*$/.test(strData) || /^\..*$/.test(strData) || /^.*@$/.test(strData) || /^.*\.$/.test(strData)) {
        return false;
    }

    return /^.+@.+\..+$/.test(strData);
}

function VerificarData(campoDataString) {
    campoDataString = campoDataString.substring(0, 10);
    var dma = -1;
    var data = Array(3);
    var ch = campoDataString.charAt(0);
    for (i = 0; i < campoDataString.length && ((ch >= '0' && ch <= '9') || (ch == '/' && i != 0));) {
        data[++dma] = '';
        if (ch != '/' && i != 0)
            return false;
        if (i != 0)
            ch = campoDataString.charAt(++i);
        if (ch == '0')
            ch = campoDataString.charAt(++i);
        while (ch >= '0' && ch <= '9') {
            data[dma] += ch;
            ch = campoDataString.charAt(++i);
        }
    }
    if (ch != '')
        return false;
    if (data[0] == '' || isNaN(data[0]) || parseInt(data[0]) < 1)
        return false;
    if (data[1] == '' || isNaN(data[1]) || parseInt(data[1]) < 1 || parseInt(data[1]) > 12)
        return false;
    if (data[2] == '' || isNaN(data[2]) || ((parseInt(data[2]) < 0 || parseInt(data[2]) > 99) && (parseInt(data[2]) < 1900 || parseInt(data[2]) > 9999)))
        return false;
    if (data[2] < 50)
        data[2] = parseInt(data[2]) + 2000;
    else if (data[2] < 100)
        data[2] = parseInt(data[2]) + 1900;
    switch (parseInt(data[1])) {
        case 2: {
            if (((parseInt(data[2]) % 4 != 0 || (parseInt(data[2]) % 100 == 0 && parseInt(data[2]) % 400 != 0)) && parseInt(data[0]) > 28) || parseInt(data[0]) > 29)
                return false;
            break;
        }
        case 4: case 6: case 9: case 11: {
            if (parseInt(data[0]) > 30)
                return false;
            break;
        } default: {
            if (parseInt(data[0]) > 31)
                return false;
        }
    }
    return true;
}

function ConfirmarExclusao(url, mensagem, tamanho) {
    var link = MontaCaminhoCompleto(url);

    var msgExclusaoDefault = "Deseja mesmo excluir?";

    var larguraDialog = 600;

    if (tamanho != undefined && tamanho != null) {
        larguraDialog = tamanho;
    }

    if (mensagem != undefined && mensagem != null && mensagem.length > 0) {
        $("#confirma-exclusao .mensagem").html(mensagem);
    }
    else {
        $("#confirma-exclusao .mensagem").html(msgExclusaoDefault);
    }

    $("#confirma-exclusao").dialog(
        {
            appendTo: 'body',
            dialogClass: 'modal',
            draggable: false,
            resizable: false,
            width: '60%',
            title: 'Atenção:',
            modal: true, open: function () { $(".ui-dialog").scrollTop("0"); },
            buttons: [{
                text: "Cancelar",
                "class": 'btn btn-primary btn-cancelar',
                click: function () { $(this).dialog("close"); }
            },
            {
                text: "Confirmar",
                "class": 'btn btn-primary',
                click: function () { window.location.href = link; $(this).dialog("close"); }
            }]
        });

    $("#confirma-exclusao").children().children().removeClass('center');
}

function ConfirmarSubmit(mensagem) {
    $("#confirma-submit .mensagem").html(mensagem);

    $("#confirma-submit").dialog(
        {
            appendTo: 'body',
            dialogClass: 'modal',
            draggable: false,
            resizable: false,
            width: '60%',
            title: 'Atenção:',
            modal: true, open: function () { $(".ui-dialog").scrollTop("0"); },
            buttons: [{
                text: "Não",
                "class": 'btn btn-primary',
                click: function () { $(this).dialog("close"); event.preventDefault(); return false; }
            },
            {
                text: "Sim",
                "class": 'btn btn-primary',
                click: function () { $(this).dialog("close"); $("form").submit(); }
            }]
        });
}
/*function Confirmar(mensagem) {
    var defer = $.Deferred();
    $("#confirma-submit .mensagem").html(mensagem);
    $("#confirma-submit").dialog({
        autoOpen: true,
        close: function () {
            $(this).dialog('destroy');
        },
        position: ['left', 'top'],
        title: 'Continue?',
        buttons: {
            "Yes": function () {
                defer.resolve(true);
                $(this).dialog("close");
            },
            "No": function () {
                defer.resolve(false);
                $(this).dialog("close");
            }
        }
    });
    return defer.promise();
}*/

//Paginação no accordion
var paginatorHandle = null;

jQuery.fn.extend({
    paginateAccordion: function (options) {
        var currentPage = options.currentPage ? parseInt(options.currentPage, 10) : 0;
        var itemsPerPage = options.itemsPerPage ? parseInt(options.itemsPerPage, 10) : 5;
        var paginatorControl = options.paginatorControl;

        return new AccordionPaginator(this, currentPage, itemsPerPage, paginatorControl);
    }
});

function AccordionPaginator(element, currentPage, itemsPerPage, paginatorControl) {
    this.element = element;
    this.currentPage = currentPage;
    this.itemsPerPage = itemsPerPage;
    this.paginatorControl = paginatorControl;

    // does the actual pagination (shows/hides items)
    this.paginate = function () {
        if (this.element.children("h2").length <= this.itemsPerPage) {
            $('#accordionPaginator').hide();
        }
        else {
            var index = this.currentPage * this.itemsPerPage;

            element.accordion("option", "activate", index);
            element.children().hide();

            if (index < 0) {
                this.element.children("h2:first").show();
            } else {
                this.element.children("h2:eq(" + index + "),h2:gt(" + index + ")")
                    .filter(":lt(" + this.itemsPerPage + ")")
                    .show();
            }

            this.refreshControl();
        }
    };

    // increments the currentPage var (if possible) and calls paginate
    this.nextPage = function () {
        if (this.currentPage + 1 >= this.getMaxPageIndex()) {
            return;
        }

        this.currentPage++;
        this.paginate();
    };

    // decrements the currentPage var (if possible) and calls paginate
    this.previousPage = function () {
        if (this.currentPage - 1 < 0) {
            return;
        }

        this.currentPage--;
        this.paginate();
    };

    // sets currentPage var (if possible) and calls paginate
    this.goToPage = function (pageIndex) {
        if ((pageIndex < 0) || (pageIndex >= this.getMaxPageIndex())) {
            return;
        }

        this.currentPage = pageIndex;
        this.paginate();
    };

    // returns the maximum of pages possible with the current number of items
    this.getMaxPageIndex = function () {
        var items = this.element.children("h2");
        var fullPages = items.length / this.itemsPerPage;
        var restPage = items.length % (this.itemsPerPage > 0 ? 1 : 0);
        return fullPages + restPage;
    };

    // fills up the paginator control
    this.refreshControl = function () {
        if (this.paginatorControl === null) {
            return;
        }

        $("#paginas").empty();
        for (var i = 0; i < this.getMaxPageIndex(); i++) {
            if (this.currentPage == i) {
                $("#paginas").append('<a class="pageButton active" onclick="paginatorHandle.goToPage(' + i + ')">' + (i + 1) + '</a>');
            }
            else {
                $("#paginas").append('<a class="pageButton" onclick="paginatorHandle.goToPage(' + i + ')">' + (i + 1) + '</a>');
            }
        }
    };
}

function AbrirDialogSair() {
    $("#sair").dialog(
        {
            appendTo: 'body',
            dialogClass: 'modal',
            draggable: false,
            resizable: false,
            width: '60%',
            title: 'Deseja realmente sair?',
            modal: true, open: function () { $(".ui-dialog").scrollTop("0"); },
            buttons: [
                {
                    text: "Cancelar",
                    "class": 'btn btn-primary btn-cancelar',
                    click: function () { $(this).dialog("close"); }
                },
                {
                    text: "Sair",
                    "class": 'btn btn-primary',
                    click: function () { RetornaCaminho("Login/Logout") }
                }]
        });
}

function MontaCaminhoCompleto(caminho) {
    // Remover todas as possíveis repetições de barras de formação da url (ex: "//Home/AcessoInicial?tipoEmpregador=geral")
    var caminhoCompleto = ($('#HiddenCurrentUrl').val() + caminho).replace(/\/+/g, '/');

    // Partir a url em tokens com o separador "/",
    // remover as duplicações sucessivas (ex: "/portalweb-completo-003/portalweb-completo-003/FolhaPagamento/Listagem/ListarPagamentos?competencia=201707")
    // e montá-la novamente
    var tokens = caminhoCompleto.split('/');
    var tokenCorrente = null;
    var i = 0;

    caminhoCompleto = '';

    for (; i < tokens.length; ++i) {
        if (tokens[i] == '' || tokenCorrente == tokens[i]) {
            continue;
        }

        tokenCorrente = tokens[i];
        caminhoCompleto += '/' + tokens[i];
    }

    return caminhoCompleto;
}

function RetornaCaminho(caminho) {
    window.location = MontaCaminhoCompleto(caminho);
}

function AbreNovaPagina(caminho) {
    var win = window.open(MontaCaminhoCompleto(caminho), '_blank');
    win.focus();
}

//TODO: Retirar a function NaoImplementado
function NaoImplementado() {
    alert("Não implementado");
    //location.reload();
    //event.stopPropagation();
    //return false;
}

// funcoes para chamadas ajax
function AjaxCall(callback, url, parametros, mensagemErro, fonte, tipoRequisicao, tempoTimeout, tipoRetorno) {
    var descricaoFonte = "";
    var endereco = MontaCaminhoCompleto(url);

    if (parametros == null) {
        parametros = {};
    }

    if (fonte == null || fonte == undefined) {
        descricaoFonte = "Geral";
    }
    else {
        descricaoFonte = fonte;
    }

    if (tipoRequisicao == null || tipoRequisicao == undefined) {
        tipoRequisicao = "get";
    }

    if (tempoTimeout == null || tempoTimeout == undefined) {
        tempoTimeout = 120000; //10seg
    }

    var options = {};

    options.url = endereco;
    options.data = parametros;
    options.type = tipoRequisicao;
    options.cache = true;
    options.async = true;
    options.timeout = tempoTimeout;
    //options.traditional = true;

    if (tipoRequisicao != 'get') {
        options.dataType = "json";
        if (tipoRetorno != null && tipoRetorno != undefined && tipoRetorno.length > 0) {
            options.dataType = tipoRetorno;
        }
        options.contentType = "application/json; charset=utf-8";
    }

    options.success = function (data) {
        if (data.Sucesso != null && data.Sucesso != undefined && !data.Sucesso) {
            if (data.Erros == undefined) {
                if (mensagemErro == null) {
                    mensagemErro = "Houve um erro inesperado no retorno da execução."
                }
                MostrarMensagem(descricaoFonte, "warning", mensagemErro, "ajax-call");
            } else {
                MostrarMensagem(descricaoFonte, "danger", data.Erros, "ajax-call");
            }
        } else {
            $("#mensagem" + descricaoFonte).children("div.ajax-call:not(.retornoServidor)").remove();
        }
        if (parametros["onload"] != undefined) {
            data["onload"] = parametros["onload"];
        }
        if (parametros["onchange"] != undefined) {
            data["onchange"] = parametros["onchange"];
        }
        if (parametros["indiceIrCompl"] != undefined) {
            data["indiceIrCompl"] = parametros["indiceIrCompl"];
        }

        if (callback != null) {
            callback(data);
        }
    };

    options.error = function (xhr, ajaxOptions, err) {
        retorno = null;
        if (parametros["onload"] != undefined) {
            retorno = { "onload": parametros["onload"] };
        }

        if (xhr.status != "0") { // ajax cancelado por refresh
            if (mensagemErro == null) {
                mensagemErro = err;
                if (mensagemErro == undefined || mensagemErro.length == 0 || err == "timeout") {
                    mensagemErro = "Houve um erro inesperado no retorno da execução.";
                }
            }
            MostrarMensagem(descricaoFonte, "warning", mensagemErro, "ajax-call");

            if ($('#loading').is(':visible')) {
                $('#loading').fadeOut();
            }

            if (callback != null) {
                callback(retorno);
            }
        }
        else {
            if ($('#loading').is(':visible')) {
                $('#loading').fadeOut();
            }

            if (callback != null) {
                callback(retorno);
            }
        }
    };

    $.ajax(options);
}

function AjaxSincronoCall(url, parametros, mensagemErro, fonte, tipoRequisicao) {

    var result = null;
    var descricaoFonte = "";
    var endereco = MontaCaminhoCompleto(url);

    if (parametros == null) {
        parametros = {};
    }

    if (fonte == null || fonte == undefined) {
        descricaoFonte = "Geral";
    }
    else {
        descricaoFonte = fonte;
    }

    if (tipoRequisicao == null || tipoRequisicao == undefined) {
        tipoRequisicao = "get";
    }

    var dataType = "";
    var contentType = "application/x-www-form-urlencoded; charset=UTF-8";

    if (tipoRequisicao != 'get') {
        dataType = "json";
        contentType = "application/json; charset=utf-8";
    }

    $.ajax({
        url: endereco,
        data: parametros,
        type: tipoRequisicao,
        cache: true,
        async: false,
        dataType: dataType,
        contentType: contentType,
        success: function (data) {
            result = data;
            if (!data.Sucesso) {
                if (data.Erros == "undefined") {
                    if (mensagemErro == null) {
                        mensagemErro = "Houve um erro inesperado no retorno da chamada Ajax."
                    }
                    MostrarMensagem(descricaoFonte, "warning", mensagemErro, "ajax-call");
                } else {
                    MostrarMensagem(descricaoFonte, "warning", data.Erros, "ajax-call");
                }
            } else {
                $("#mensagem" + descricaoFonte).children("div.ajax-call").remove();
                if (parametros["onload"] != undefined) {
                    data["onload"] = parametros["onload"];
                }

                result = data;
            }
        },
        error: function (xhr, ajaxOptions, err) {
            if (mensagemErro == null) {
                mensagemErro = err;
            }
            MostrarMensagem(descricaoFonte, "warning", mensagemErro, "ajax-call");
            if (parametros["onload"] != undefined) {
                result = { "onload": parametros["onload"] };
            }
        }
    });

    return result;
}

function format(str, obj) {
    return str.replace(/\{\s*([^}\s]+)\s*\}/g, function (m, p1, offset, string) {
        return obj[p1]
    })
}

function removerAcentos(newStringComAcento) {
    var string = newStringComAcento;
    var mapaAcentosHex = {
        a: /[\xE0-\xE6]/g,
        e: /[\xE8-\xEB]/g,
        i: /[\xEC-\xEF]/g,
        o: /[\xF2-\xF6]/g,
        u: /[\xF9-\xFC]/g,
        c: /\xE7/g,
        n: /\xF1/g
    };

    for (var letra in mapaAcentosHex) {
        var expressaoRegular = mapaAcentosHex[letra];
        string = string.replace(expressaoRegular, letra);
    }

    return string;
}
function pad(value, totalWidth, paddingChar) {
    var length = totalWidth - value.toString().length + 1;
    if (length < 0) {
        return value;
    }
    return Array(length).join(paddingChar || '0') + value;
}

String.prototype.ReplaceAll = function (target, replacement) {
    return this.split(target).join(replacement);
};

function CalcularIdadeEmAnos(dataInicial, dataFinal) {
    var anos = dataFinal.getYear() - dataInicial.getYear();

    if (anos < 0) {
        return 0;
    }

    if (dataFinal.getMonth() < dataInicial.getMonth() || (dataFinal.getMonth() === dataInicial.getMonth() && dataFinal.getDate() < dataInicial.getDate())) {
        anos--;
    }

    return anos;
}

// Força o firefox a recarregar a página quando clica no botão voltar (mais detalhes: https://madhatted.com/2013/6/16/you-do-not-understand-browser-history)
$(window).unload(function () { });

// Polyfill : Math.trunc() incompativel com IE
if (!Math.trunc) {
    Math.trunc = function (v) {
        return v < 0 ? Math.ceil(v) : Math.floor(v);
    };
}

function TratarIntegracaoSGD(idServico, idOrgao, idEvento) {

    if (idServico != undefined && idServico.length > 0 && idOrgao != undefined && idOrgao.length > 0) {
        var parametros = { 'idServico': idServico, 'idOrgao': idOrgao, 'idEvento': idEvento }

        AjaxCall(RetornoTratarIntegracaoSGD, "IntegracaoSGD/ObterLinkFormularioAvaliacao/", parametros, "Erro ao tratar integração com SGD.", null);
    }
}

function RetornoTratarIntegracaoSGD(data) {
    if (data != null && data.Sucesso) {
        var url = data.Objeto["Url"];

        if (url != undefined && url.length > 0) {

            window.open(url, "_blank");
            return;
        }
    }
}

function runSpeechRecognition(fase) {
    var anos = ["2015", "2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023", "2024", "2025"];
    var meses = ["janeiro", "fevereiro", "marco", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro", "decimo terceiro", "13º"]
    var fecharFolha = ["fechar folha", "encerrar folha", "opcao um", "opcao dois", "opcao 1", "opcao 2", "gerar dae", "gerar di", "gerar day", "gerar design", "gerar dai", "gerar dar", "gerar darf"]

    // new speech recognition object
    var SpeechRecognition = SpeechRecognition || webkitSpeechRecognition;
    var recognition = new SpeechRecognition();
    //var recognition = new webkitSpeechRecognition();
    // Define whether continuous results are returned for each recognition
    // or only a single result. Defaults to false
    //recognition.continuous = true;
    // Controls whether interim results should be returned 
    // Interim results are results that are not yet final 
    // (e.g. the SpeechRecognitionResult.isFinal property is false.)
    //recognition.interimResults = true;
    // Returns and sets the language of the current SpeechRecognition. 
    // If not specified, this defaults to the HTML lang attribute value
    // or the user agent's language setting if that isn't set either.
    // There are a lot of supported languages (go to supported languages at the end of the article)
    recognition.lang = "pt-BR";
    // This runs when the speech recognition service starts
    recognition.onstart = function () {

        //$("#assistente").removeClass("hide");
        //$("#assistente").show();
        if (fase == 0) {
            var parametros = {
                "comando": "assistente social"
            }
            //recognition.stop();
            AjaxCall(RetornoRecognition, "Home/ExecutarComandoDeVozAsync", parametros);
            //ManterFundoEscutando(12000);
        }


    };

    recognition.onend = function () {

        $("#assistente").addClass("hide");
        $("#assistente").hide();
    }

    recognition.onspeechend = function () {
        recognition.stop();
    }

    // This runs when the speech recognition service returns result
    recognition.onresult = function (event) {

        var transcript = event.results[0][0].transcript;
        transcript = removeAcento(transcript);
        transcript = transcript.toLowerCase().replace('.', '').replace(',', '').replace('!', '').replace('?', '');
        if (transcript == "março") {
            transcript = "marco";
        }
        var confidence = event.results[0][0].confidence;

        /*if (fase == 0) {
            if (transcript.includes("social") && transcript.includes("assistente")) {
                AjaxCall(RetornoRecognition, "Home/ExecutarComandoDeVozAsync", parametros);
                // window.location.href = "https://localhost:44356/assistente/executar";
            }
            else {
                runSpeechRecognition(fase);
            }
        }
        else */if (fase == 1) {
            if (fecharFolha.includes(transcript)) {
                var parametros = {
                    "comando": transcript,
                    "fase": fase
                }
                recognition.stop();
                AjaxCall(RetornoRecognition, "Home/ExecutarComandoDeVozAsync", parametros);
            }
            else {
                var utterThis = new SpeechSynthesisUtterance("Não entendi o comando. Favor repetir");
                speechSynthesis.speak(utterThis);
                utterThis.onend = function (event) {
                    speechSynthesis.cancel();
                    $("#assistente").removeClass("hide");
                    $("#assistente").show();
                    runSpeechRecognition(fase);
                }
            }
        }
        //Ano
        else if (fase == 2 || fase == 6) {
            var achou = "false";
            for (let i = 0; i < anos.length; i++) {

                if (transcript.includes(anos[i])) {
                    achou = "true";
                    var parametros = {
                        "comando": anos[i],
                        "fase": fase
                    }
                    recognition.stop();
                    AjaxCall(RetornoRecognition, "Home/ExecutarComandoDeVozAsync", parametros);
                    break;
                }

            }
            if (achou == "false") {
                recognition.stop();
                var utterThis = new SpeechSynthesisUtterance("Não entendi o comando. Favor repetir");
                speechSynthesis.speak(utterThis);
                utterThis.onend = function (event) {
                    speechSynthesis.cancel();
                    $("#assistente").removeClass("hide");
                    $("#assistente").show();
                    runSpeechRecognition(fase);
                }



            }
        }
        //Mes
        else if (fase == 3 || fase == 7) {
            var achou = "false";
            for (let i = 0; i < meses.length; i++) {

                if (transcript.includes(meses[i])) {
                    achou = "true";
                    var parametros = {
                        "comando": meses[i],
                        "fase": fase
                    }
                    recognition.stop();
                    AjaxCall(RetornoRecognition, "Home/ExecutarComandoDeVozAsync", parametros);
                }

            }
            if (achou == "false") {
                recognition.stop();
                var utterThis = new SpeechSynthesisUtterance("Não entendi o comando. Favor repetir");
                speechSynthesis.speak(utterThis);
                utterThis.onend = function (event) {
                    speechSynthesis.cancel();
                    $("#assistente").removeClass("hide");
                    $("#assistente").show();
                    runSpeechRecognition(fase);
                }
            }
        }
        // output.innerHTML = "<b>Text:</b> " + transcript + "<br/> <b>Confidence:</b> " + confidence * 100 + "%";
        // output.classList.remove("hide");
        else {
            runSpeechRecognition(fase);
        }
    };

    // start recognition
    recognition.start();
}

function RetornoRecognition(data) {
    if (data != null && data.Sucesso) {
        var utterThis = new SpeechSynthesisUtterance(data.Mensagem);
        speechSynthesis.speak(utterThis);
        utterThis.onend = function (event) {
            speechSynthesis.cancel();
            if (data.SubCodigo != 3 && data.SubCodigo != 7) {
                $("#assistente").removeClass("hide");
                $("#assistente").show();
            }
            /*if (data.Mensagem.length > 50) {
                ManterFundoEscutando(5000);
            } else {

                ManterFundoEscutando(5000);
            }*/

            if (data.SubCodigo == 0) {
                fase = 1;
            }
            //Ano
            else if (data.SubCodigo == 1) {
                fase = 2;
            }
            else if (data.SubCodigo == 2) {
                fase = 3;
            }
            else if (data.SubCodigo == 3) {
                fase = 4;
                //Acessando Folha
                var parametros = {
                    "comando": "Acessando folha"
                }
                AjaxCall(RetornoRecognition, "Home/ExecutarComandoDeVozAsync", parametros);


            } else if (data.SubCodigo == 4) {
                fase = 5;
                //Emitindo DAE
                EmitirGuia(fase, data.Competencia);
            }
            else if (data.SubCodigo == 5) {
                fase = 6;
            }
            //Ano
            else if (data.SubCodigo == 6) {
                fase = 7;
            }
            //Mes
            else if (data.SubCodigo == 7) {
                fase = 8;
                //Emitindo DAE
                EmitirGuia(fase, data.Competencia);

            }
            runSpeechRecognition(fase);
        }
        //speechSynthesis.speak(new SpeechSynthesisUtterance(data.Mensagem));




    } else if (data != null) {
        //var data64 = _arrayBufferToBase64(data);
        //var sampleArr = base64ToArrayBuffer(data);
        //data = data.replaceAll("\"", "");
        //DownloadFile("GuiaPagamento.pdf", data);
        speechSynthesis.speak(new SpeechSynthesisUtterance("Ocorreu um erro no assistente de voz"));
        $("#assistente").addClass("hide");
        $("#assistente").hide();
    }
    else {
        if (fase == 4) {
            speechSynthesis.speak(new SpeechSynthesisUtterance("Ocorreu um erro ao fechar a folha"));
            $("#assistente").addClass("hide");
            $("#assistente").hide();
        }
        else if (fase == 7) {
            speechSynthesis.speak(new SpeechSynthesisUtterance("Ocorreu um erro ao gerar o DAE"));
            $("#assistente").addClass("hide");
            $("#assistente").hide();
        } else {
            speechSynthesis.speak(new SpeechSynthesisUtterance("Ocorreu um erro no assistente de voz"));
            $("#assistente").addClass("hide");
            $("#assistente").hide();
        }
    }
}


function ManterFundoEscutando(tempo) {
    $("#assistente").removeClass("hide");
    $("#assistente").show();
    setTimeout(() => console.log("sleep"), tempo);
}
function EmitirGuia(fase, competencia) {
    /*var parametros = {
        "comando": "Emitindo DAE",
        "fase": fase
    }
    AjaxCall(GerarDAE, "Home/EmitindoDAEAsync", parametros, null, null, null, null, 'arraybuffer');*/
    const link = document.createElement('a');
    //link.href = MontaCaminhoCompleto('Home/EmitindoDAEAsync?comando=' + 'Emitindo DAE'+'&fase='+fase);
    link.href = MontaCaminhoCompleto('Home/IrParaFolhaFechada?competencia=' + competencia);
    //link.setAttribute('download', 'GuiaPagamento.pdf');



    document.body.appendChild(link);
    if (fase == 5) {
        speechSynthesis.speak(new SpeechSynthesisUtterance("Redirecionando para a folha fechada"));
    } else {
        speechSynthesis.speak(new SpeechSynthesisUtterance("Redirecionando para o download do DAE"));
    }

    link.click();
    $('#loading').show();
}

function removeAcento(text) {
    text = text.toLowerCase();
    text = text.replace(new RegExp('[ÁÀÂÃ]', 'gi'), 'a');
    text = text.replace(new RegExp('[ÉÈÊ]', 'gi'), 'e');
    text = text.replace(new RegExp('[ÍÌÎ]', 'gi'), 'i');
    text = text.replace(new RegExp('[ÓÒÔÕ]', 'gi'), 'o');
    text = text.replace(new RegExp('[ÚÙÛ]', 'gi'), 'u');
    text = text.replace(new RegExp('[Ç]', 'gi'), 'c');
    return text;
}

function ObterDescricaoTipoInscricao(iTipoInscricao) {
    if (iTipoInscricao == undefined || iTipoInscricao == 0) {
        return "-"
    }

    return iTipoInscricao == 1 ? "1 - CNPJ" : "2 - CPF";
}

function ObterDescricaoTipoProcesso(iTipoProcesso) {
    if (iTipoProcesso == undefined || iTipoProcesso == 0) {
        return "-"
    }

    return iTipoProcesso == 1 ? "1 - Administração" : "2 - Judicial";
}

// "1=Privada;2=FAPI;3=Funpresp"
function ObterDescricaoTipoPrevidenciaComplementar(iTipoPrevidenciaComplementar) {
    var parametros = { 'iTipoPrevidenciaComplementar': iTipoPrevidenciaComplementar }
    var url = "FolhaPagamento/PagamentoCompleto/ObterDescricaoTipoPrevidenciaComplementar/";
    var descricao = "-";

    var data = AjaxSincronoCall(url, parametros, "Erro ao tentar recuperar descrição do tipo da previdência complementar.", null);

    if (data != null && data.Sucesso) {
        var descricao = data.Objeto["Descricao"];
    }

    return descricao;
}


function ObterDescricaoTipoRendimento(iTipoRendimento, campo, divMensagem) {
    var parametros = { 'iTipoRendimento': iTipoRendimento, 'campo': campo }
    var url = "FolhaPagamento/PagamentoCompleto/ObterDescricaoTipoRendimento/";
    var descricao = "-";

    var data = AjaxSincronoCall(url, parametros, "Erro ao tentar recuperar descrição do tipo de rendimento.", divMensagem);

    if (data != null && data.Sucesso) {
        var descricao = data.Objeto["Descricao"];
    }

    return descricao;
}

function ObterDescricaoOrigemReembolso(iOrigemReembolso) {
    var parametros = { 'iOrigemReembolso': iOrigemReembolso }
    var url = "FolhaPagamento/PagamentoCompleto/ObterDescricaoOrigemReembolso/";
    var descricao = "-";

    var data = AjaxSincronoCall(url, parametros, "Erro ao tentar recuperar descrição da origem do reembolso.", null);

    if (data != null && data.Sucesso) {
        var descricao = data.Objeto["Descricao"];
    }

    if (descricao.length > 50) {
        return iOrigemReembolso + " - " + descricao.substring(0, 50) + "...";
    }
    else {
        return iOrigemReembolso + " - " + descricao;
    }

}

function isUndefinedOrNull(x) {
    return typeof x === 'undefined' || x === null;
}

function getStringValue(x) {
    if (isUndefinedOrNull(x)) {
        return '';
    }

    return `${x}`;
}
async function doIAAjax(texto) {
    const result = await $.ajax({
        url: "http://127.0.0.1:5000/enviarMensagem?mensagem=" + texto,
        type: 'GET',
        withCredentials: true,
    });

    return result;
}

async function getIA(texto) {
    $("#loading").show();
    var res = await doIAAjax(texto);
    regex = /\[\[\d+\]\]\(https:\/\/poe\.com\/citation\?.*?citation=\d+\)/g;
    respostaLimpa = res.replace(regex, "");
    $('#loading').fadeOut();
    return respostaLimpa;
}
async function AbrirModalIAAssistente(texto) {
    resposta = await getIA(texto);
    $("#texto-ia").text(resposta);
    $("#dialog-ia-assistente").dialog(
        {
            appendTo: 'body',
            position: ['center', 'center'],
            dialogClass: 'modal',
            draggable: false,
            resizable: false,
            width: 600,
            title: 'Assistente eSocial:',
            modal: true, open: function () { $(".ui-dialog").scrollTop("0"); },
            buttons: [
                {
                    text: "Ok",
                    "class": 'btn btn-primary',
                    click: function () { $(this).dialog("close"); }
                }]
        });
}


//Chatbot
function abrirIframeChatbot() {
    $("#iframeChatbot").css("display", "block");
    $("#chatbot-assistente-close").css("display", "block");
    $("#chatbot-assistente-trigger").css("display", "none");

}
function fecharIframeChatbot() {
    $("#iframeChatbot").css("display", "none");
    //$("#iframeChatbot", window.parent.document).remove();
    $("#chatbot-assistente-trigger").css("display", "block");
    $("#chatbot-assistente-close").css("display", "none");

}
async function enviarMsgChatbot() {
    // var pergunta = $('#chatbot-simple-iframe').contents().find('#chatbot-conversa').val();
    var pergunta = $('#chatbot-conversa').val();
    $('#chatbot-conversa').val("");
    adicionarPergunta(pergunta);
    $(".chatbot-busy").attr("style", "display:block");
    adicionarResposta(pergunta);


}
function adicionarPergunta(pergunta) {
    var perguntaHtml = '<div class="chatbot-message chatbot-you"><div class="chatbot-text">' + pergunta + '</div></div> ';
    $('#chatbot-chat').append(perguntaHtml);
}
async function adicionarResposta(pergunta) {
    var resposta = await getIA(pergunta);
    var respostaHtml = '<div class="chatbot-message chatbot-other"><div class="chatbot-text">' + resposta + '</div></div>';
    $('#chatbot-chat').append(respostaHtml);
    $(".chatbot-busy").attr("style", "display:none");
}

function adicionarPerguntaSync(pergunta) {
    var perguntaHtml = '<div class="chatbot-message chatbot-you"><div class="chatbot-text">' + pergunta + '</div></div> ';
    $('#iframeChatbot').contents().find("#chatbot-chat").append(perguntaHtml);

}
function adicionarRespostaSync(resposta) {
    if (resposta != "Eu sou o Assistente eSocial! Como posso te ajudar?") {
        var respostaHtml = '<div class="chatbot-message chatbot-other"><div class="chatbot-text">' + resposta + '</div></div>';
        $('#iframeChatbot').contents().find('#chatbot-chat').append(respostaHtml);
        $('#iframeChatbot').contents().find(".chatbot-busy").attr("style", "display:none");
    }
}

;
$(document).ready(function () {
    var logado = true;
    var informacoes = {};
    var urlWebService;

    if (document.URL.indexOf("esocial.desenv") != -1) {
        logado = false;
        urlWebService = "https://login.esocial.desenv.serpro/api/v1/LoginESocialConsultas.svc/DadosSessao";
    }
    else if (document.URL.indexOf("esocial.teste") != -1) {
        logado = false;
        urlWebService = "https://login.esocial.teste.serpro/api/v1/LoginESocialConsultas.svc/DadosSessao";
    }
    else if (document.URL.indexOf("esocial.val") != -1) {
        logado = false;
        urlWebService = "https://login.esocial.val.serpro/api/v1/LoginESocialConsultas.svc/DadosSessao";
    }
    else if (document.URL.indexOf("hom.esocial") != -1) {
        urlWebService = "https://login.hom.esocial.gov.br/api/v1/LoginESocialConsultas.svc/DadosSessao";
    }
    else if (document.URL.indexOf("esocial.hom") != -1) {
        urlWebService = "https://login.hom.esocial.gov.br/api/v1/LoginESocialConsultas.svc/DadosSessao";
    }
    else if (document.URL.indexOf("producaorestrita.esocial") != -1) {
        urlWebService = "https://login.producaorestrita.esocial.gov.br/api/v1/LoginESocialConsultas.svc/DadosSessao";
    }
    else if (document.URL.indexOf("localhost") != -1) {
        //urlWebService = "http://" + document.location.host + "/ControllerPadrao/RecuperarIdentidade";
        logado = false;
    }
    else {
        urlWebService = "https://login.esocial.gov.br/api/v1/LoginESocialConsultas.svc/DadosSessao";
    }


    // Mock com informacoes DadosContaGovBr
    ////var data = JSON.parse('{"ComCertificadoDigital":false,"ComProcuracao":false,"DadosContaGovBr":{"TipoAcessoGovBR":"passwd","NiveisAutenticacaoGovBR":[1],"SelosAutenticacaoGovBR":{"801":"certificado_digital"},"UsoDeDuploFatorDeAutenticacao":false},"HoraLogin":"/Date(1670351804897-0300)/","HoraUltimoAcesso":"/Date(1670351834177-0300)/","IDSessao":"a606515ff8f620136b26525f7aa58fd6347344c61b603735a4aac972e3ebb87c","LoginViaGovBr":true,"NI":"05033686607","NIProcurador":null,"Nome":"EDUARDO RESENDE GOMES","NomeProcurador":null,"Origem":"govbr","ThumbprintCertificado":"BACEDD641B91CDB7C4F6AABA132ED2C6AFB4ED0C","Timeout":10,"TipoNI":"PESSOA_FISICA"}');

    // Mock sem informacoes DadosContaGovBr
    // var data = JSON.parse('{"ComCertificadoDigital":true,"ComProcuracao":false,"HoraLogin":"/Date(1670351804897-0300)/","HoraUltimoAcesso":"/Date(1670351834177-0300)/","IDSessao":"a606515ff8f620136b26525f7aa58fd6347344c61b603735a4aac972e3ebb87c","LoginViaGovBr":true,"NI":"05033686607","NIProcurador":null,"Nome":"EDUARDO RESENDE GOMES","NomeProcurador":null,"Origem":"govbr","ThumbprintCertificado":"BACEDD641B91CDB7C4F6AABA132ED2C6AFB4ED0C","Timeout":10,"TipoNI":"PESSOA_FISICA"}');

    // Mock: Codigo de acesso, Usuario/CodAcesso/Senha
    // var data = JSON.parse('{ "ComCertificadoDigital": false, "ComProcuracao": false, "DadosContaGovBr": null, "HoraLogin": "/Date(1671296200413-0300)/", "HoraUltimoAcesso": "/Date(1671296222887-0300)/", "IDSessao": "ae137e16c220e1c96978b227aa703ee36c2c67eeb1cf7fb4e0e6dd356ebf0d46", "LoginViaGovBr": false, "NI": "05163217658", "NIProcurador": null, "Nome": "JULIO CESAR PEREIRA ANTUNES", "NomeProcurador": null, "Origem": "esocial", "ThumbprintCertificado": "000000000000", "Timeout": 10, "TipoNI": "PESSOA_FISICA" }');

    // Mock: Login HOM, Gov br, Usuario / Senha
    // var data = JSON.parse('{ "ComCertificadoDigital": false, "ComProcuracao": false, "DadosContaGovBr": { "TipoAcessoGovBR": "passwd", "NiveisAutenticacaoGovBR": [3], "SelosAutenticacaoGovBR": { "801": "certificado_digital" }, "UsoDeDuploFatorDeAutenticacao": false }, "HoraLogin": "/Date(1670092540877-0300)/", "HoraUltimoAcesso": "/Date(1670092557283-0300)/", "IDSessao": "8c8ab9e9b00c7bcaae624ea45a4b65515f803f789641fc3bcfe442e09c80910c", "LoginViaGovBr": true, "NI": "05163217658", "NIProcurador": null, "Nome": "QFORL XVHZI KVIVRIZ ZMGFMVH", "NomeProcurador": null, "Origem": "govbr", "ThumbprintCertificado": "000000000000", "Timeout": 10, "TipoNI": "PESSOA_FISICA" }');

    // Mock: Login HOM, Gov br, Certificado digital
    // var data = JSON.parse('{"ComCertificadoDigital":true,"ComProcuracao":false,"DadosContaGovBr":{ "TipoAcessoGovBR":"x509","NiveisAutenticacaoGovBR":[3],"SelosAutenticacaoGovBR":{"801":"certificado_digital"},"UsoDeDuploFatorDeAutenticacao":false}, "HoraLogin": "/Date(1670092219580-0300)/", "HoraUltimoAcesso": "/Date(1670092231817-0300)/", "IDSessao": "1b79c9459ea0d3a9c1cf1f8b4582ec5ca668c3dbbdd2aec94b94863829cc28a9", "LoginViaGovBr": true, "NI": "05163217658", "NIProcurador": null, "Nome": "HOM JULIO", "NomeProcurador": null, "Origem": "govbr", "ThumbprintCertificado": "CB1CB2FDD65D2664C87667B2BDDD5BE94AD3DCDA", "Timeout": 10, "TipoNI": "PESSOA_FISICA" }');


    /*var x = JSON.stringify(data.DadosContaGovBr);

    dataJson = JSON.parse(x);

    var tipoAcessoGovBr = "";
    var seloGovBr = "1";
    var origem = "esocial";

    if (dataJson != null && dataJson != undefined) {
        if (dataJson.TipoAcessoGovBR != null && dataJson.TipoAcessoGovBR != undefined) {
            tipoAcessoGovBr = dataJson.TipoAcessoGovBR;
        }

        if (data.Origem != null && data.Origem != undefined) {
            origem = data.Origem;
        }

        if (dataJson.NiveisAutenticacaoGovBR != null && dataJson.NiveisAutenticacaoGovBR != undefined) {
            seloGovBr = dataJson.NiveisAutenticacaoGovBR[0];
        }
    }

    ////alert("tipoacesso: " + tipoAcessoGovBr);
    ////alert("selo: " + seloGovBr);

    //if (tipoAcessoGovBr != "" && ($.cookie("TipoAcessoGovBr") == undefined || $.cookie("TipoAcessoGovBr") == "")) {
    $.cookie("TipoAcessoGovBr", tipoAcessoGovBr);
    //}

    //if (seloGovBr != "" && ($.cookie("SeloGovBr") == undefined || $.cookie("SeloGovBr") == "")) {
    $.cookie("SeloGovBr", seloGovBr);
    //}

    //if (origem != "" && ($.cookie("Origem") == undefined || $.cookie("Origem") == "")) {
    $.cookie("Origem", origem);
    //}*/


    if (logado) {
        $.ajax({
            dataType: 'jsonp',
            url: urlWebService,
            success: function (data, textStatus) {

                var tipoAcessoGovBr = "";
                var seloGovBr = "1";
                var origem = "esocial";


                if (data == null) {
                    logado = false;
                    ////alert('data==null');

                    MontarCabecalho(logado, informacoes);
                    adequarLarguraItensMenuPrincipal();
                }
                else {

                    var dataJson = JSON.parse(data.DadosContaGovBr);

                    if (dataJson != null && dataJson != undefined) {
                        if (dataJson.TipoAcessoGovBR != null && dataJson.TipoAcessoGovBR != undefined) {
                            tipoAcessoGovBr = dataJson.TipoAcessoGovBR;
                        }

                        if (dataJson.NiveisAutenticacaoGovBR != null && dataJson.NiveisAutenticacaoGovBR != undefined) {
                            seloGovBr = dataJson.NiveisAutenticacaoGovBR[0];
                        }

                        if (data.Origem != null && data.Origem != undefined) {
                            origem = data.Origem;
                        }
                    }

                    /*alert("tipoacesso: " + tipoAcessoGovBr);
                    alert("selo: " + seloGovBr);
                    alert("origem" + origem);*/

                    // Relato 3861703 - retirar modal
                    /*var currentUrl = window.location.href.toLowerCase();

                    if (currentUrl.indexOf("home/inicial") > -1) {
                        if ($('#MarcouCheckPopup').val() == "False") {
                            if (origem == "esocial" || (tipoAcessoGovBr == "passwd" && (seloGovBr == 1 || seloGovBr == 2))) {
                                AbrirModalAlertaCodigoAcesso();
                            }
                        }
                    }*/

                    //if (tipoAcessoGovBr != "" && (getCookie("TipoAcessoGovBr") == undefined || getCookie("TipoAcessoGovBr") == "")) {
                    document.cookie = "TipoAcessoGovBr = " + tipoAcessoGovBr;
                    //}

                    //if (seloGovBr != "" && (getCookie("SeloGovBr") == undefined || getCookie("SeloGovBr") == "")) {
                    document.cookie = "SeloGovBr = " + seloGovBr;
                    //}

                    //if (origem != "" && (getCookie("Origem") == undefined || getCookie("Origem") == "")) {
                    document.cookie = "Origem = " + origem;
                    //}

                    logado = true;
                    informacoes = data;

                    if ($('#EhProcurador').length > 0 || $('#EhControlador').length > 0 || $('#EhRepresentanteLegal').length > 0 || $('#EhJudiciarioOperador').length > 0) {
                        informacoes = ExtrairValoresCookieUsuarioLogado(informacoes);
                    }

                    MontarCabecalho(logado, informacoes);
                    adequarLarguraItensMenuPrincipal();
                }
            },
            error: function (xhr, textStatus, errorThrown) {
                logado = false;

                MontarCabecalho(logado, informacoes);
                adequarLarguraItensMenuPrincipal();
            }
        });

        var currentUrl = window.location.href.toLowerCase();

        if (currentUrl.indexOf("home/inicial") > -1) {
            var exibeMensagemAlerta = $('#ProblemaIRRF').val() == "True";
            if (exibeMensagemAlerta) {
                AbrirModalAlertaProblemaIRRF();
            }

            // Claudia Behring 29/02/2024 - Retirado a pedido do cliente
            //if ($('#ListaProcessoErroBaseCalculoParaMensagem').length > 0) {
            //    const textoProcessosErroBaseCalculo = `${$('#ListaProcessoErroBaseCalculoParaMensagem').val()}`;

            //    if (textoProcessosErroBaseCalculo.length > 0) {
            //        AbrirModalAlertaProblemaProcessoErroBaseCalculo(textoProcessosErroBaseCalculo);
            //    }
            //}
        }
    } else {
        informacoes = ExtrairValoresCookieUsuarioLogado(informacoes);
        logado = informacoes.Logado;

        MontarCabecalho(logado, informacoes);
        adequarLarguraItensMenuPrincipal();
    }

});

// Relato 3861703 - retirar modal
/*function AbrirModalAlertaCodigoAcesso() {

    // Após clicar em ok não exibir o popup novamente
    /*if ($('#OkCodigoAcesso').val() != 0) {
        return;
    }*x/

    var largura = 600; //// window.innerWidth * 0.8;
    /*if (largura < 600) {
        largura = 600;
    }*x/

    $("#dialog-alerta-termino-codigo-acesso").dialog(
        {
            appendTo: 'body',
            position: ['center', 50],
            dialogClass: 'modalOkCancelar modal',
            draggable: false,
            resizable: false,
            width: largura,
            title: 'Alerta - Término do Código de Acesso',
            modal: true, open: function () { $(".ui-dialog").scrollTop("0"); },
            buttons: [
                {
                    text: "OK",
                    "class": 'btn-codigo-acesso btn btn-primary',
                    width: 70,
                    click: function () {
                        ////$('#OkCodigoAcesso').val('1');
                        $("#CheckCienteCodigoAcesso").attr('checked', false);
                        $(".btn-codigo-acesso").hide();

                        // Chama ajax para marcar que o empregador está ciente
                        AjaxCall(RetornoCabecalho, "Home/MarcarCheckPopup", null);

                        $(this).dialog("close");
                    },
                }]
        }).css('max-height', '340px');

    $(".btn-codigo-acesso").hide();

    $("#CheckCienteCodigoAcesso").change(function () {
        if (this.checked) {
            $(".btn-codigo-acesso").show();
        }
        else {
            $(".btn-codigo-acesso").hide();
        }
    });
}*/


function AbrirModalAlertaProblemaIRRF() {

    var largura = 600;

    $("#dialog-alerta-mensagem-irrf").dialog(
        {
            appendTo: 'body',
            position: ['center', 50],
            dialogClass: 'modalOkCancelar modal',
            draggable: false,
            resizable: false,
            width: largura,
            title: 'Atenção',
            modal: true, open: function () { $(".ui-dialog").scrollTop("0"); },
            buttons: [
                {
                    text: "OK",
                    "class": 'btn-alerta btn btn-primary',
                    width: 70,
                    click: function () {
                        ////$('#OkCodigoAcesso').val('1'); 

                        $(this).dialog("close");
                    },
                }]
        }).css('max-height', '340px');
}

function AbrirModalAlertaProblemaProcessoErroBaseCalculo(textoProcessosErroBaseCalculo) {
    $('#numeros-processos-erro-base-calculo').text(textoProcessosErroBaseCalculo);

    $("#dialog-alerta-mensagem-processo-base-calculo").dialog(
        {
            appendTo: 'body',
            position: ['center', 'center'],
            dialogClass: 'modalOkCancelar modal',
            draggable: false,
            resizable: false,
            width: 600,
            title: 'Atenção',
            modal: true, open: function () { $(".ui-dialog").scrollTop("0"); },
            buttons: [
                {
                    text: "OK",
                    "class": 'btn-alerta btn btn-primary',
                    width: 70,
                    click: function () {
                        $(this).dialog("close");
                    },
                }]
        }).css('max-height', '340px');
}

function RetornoCabecalho(data) {
    return;
}

function ExtrairValoresCookieUsuarioLogado(informacoes) {

    /*if (document.cookie.match('ESOCIAL_NONCE_GOVBR')) {
        informacoes.Logado = true;
        var re = new RegExp("ESOCIAL_NONCE_GOVBR=([^;]+)");
        var value = re.exec(document.cookie);

        if (value != null && value != undefined) {
            var valoresCookie = value[1].split('&');

            for (i = 0; i < valoresCookie.length; i++) {
                var valor = valoresCookie[i].split('=');

                alert('a' + valor[0]);
            }
        }
    }*/

    if (document.cookie.match('UsuarioLogado=')) {
        informacoes.Logado = true;
        var re = new RegExp("UsuarioLogado=([^;]+)");
        var value = re.exec(document.cookie);


        if (value != null && value != undefined) {
            var valoresCookie = value[1].split('&');

            for (i = 0; i < valoresCookie.length; i++) {
                var valor = valoresCookie[i].split('=');

                if (valor[0] == "NI") {
                    informacoes.NI = valor[1];
                }
                else if (valor[0] == "Nome") {
                    var indiceNome = value[1].indexOf("Nome=");
                    var indiceTipoNI = value[1].indexOf("&TipoNI");

                    var nome = value[1].substring(indiceNome + 5, indiceTipoNI);

                    if (nome.indexOf("&") > 0) {
                        informacoes.Nome = nome;
                    }
                    else {
                        informacoes.Nome = valor[1];
                    }

                    if (informacoes.Nome.length > 120) {
                        informacoes.Nome = informacoes.Nome.substring(0, 114) + " (...)";
                    }
                }
                else if (valor[0] == "TipoNI") {
                    informacoes.TipoNI = valor[1];
                }
                else if (valor[0] == "ComProcuracao") {
                    informacoes.ComProcuracao = valor[1].toLowerCase() == 'true';
                }
                else if (valor[0] == "NIProcurador") {
                    informacoes.NIProcurador = valor[1];
                }
                else if (valor[0] == "NomeProcurador") {
                    informacoes.NomeProcurador = valor[1];
                    if (informacoes.NomeProcurador.length > 120) {
                        informacoes.NomeProcurador = informacoes.NomeProcurador.substring(0, 114) + " (...)";
                    }
                }
                else if (valor[0] == "TipoNIProcurador") {
                    informacoes.TipoNIProcurador = valor[1];
                }
                else if (valor[0] == "Controlador") {
                    informacoes.Controlador = valor[1].toLowerCase() == 'true';
                }
                else if (valor[0] == "NIControlador") {
                    informacoes.NIControlador = valor[1];
                }
                else if (valor[0] == "NomeControlador") {
                    informacoes.NomeControlador = valor[1];
                    if (informacoes.NomeControlador.length > 120) {
                        informacoes.NomeControlador = informacoes.NomeControlador.substring(0, 114) + " (...)";
                    }
                }
                else if (valor[0] == "TipoNIControlador") {
                    informacoes.TipoNIControlador = valor[1];
                }
                else if (valor[0] == "PerfilControlador") {
                    informacoes.PerfilControlador = valor[1];
                }
                else if (valor[0] == "JudiciarioOperador") {
                    informacoes.JudiciarioOperador = valor[1].toLowerCase() == 'true';
                }
                else if (valor[0] == "NIJudiciarioOperador") {
                    informacoes.NIJudiciarioOperador = valor[1];
                }
                else if (valor[0] == "NomeJudiciarioOperador") {
                    informacoes.NomeJudiciarioOperador = valor[1];
                    if (informacoes.NomeJudiciarioOperador.length > 120) {
                        informacoes.NomeJudiciarioOperador = informacoes.NomeJudiciarioOperador.substring(0, 114) + " (...)";
                    }
                }
                else if (valor[0] == "TipoNIJudiciarioOperador") {
                    informacoes.TipoNIJudiciarioOperador = valor[1];
                }
                else if (valor[0] == "NumeroProcessoJudiciarioOperador") {
                    informacoes.NumeroProcessoJudiciarioOperador = valor[1];
                }
                else if (valor[0] == "PerfilJudiciarioOperador") {
                    informacoes.PerfilJudiciarioOperador = valor[1];
                }
                else if (valor[0] == "RepresentanteLegal") {
                    informacoes.RepresentanteLegal = valor[1].toLowerCase() == 'true';
                }
                else if (valor[0] == "NIRepresentante") {
                    informacoes.NIRepresentante = valor[1];
                }
                else if (valor[0] == "NomeRepresentante") {
                    informacoes.NomeRepresentante = valor[1];
                    if (informacoes.NomeRepresentante.length > 120) {
                        informacoes.NomeRepresentante = informacoes.NomeRepresentante.substring(0, 114) + " (...)";
                    }
                }
                else if (valor[0] == "TipoNIRepresentante") {
                    informacoes.TipoNIRepresentante = valor[1];
                }

                // ...
                /*else if (valor[0] == "DadosContaGovBr") {
                    informacoes.DadosContaGovBr = valor[1];
                }*/
                else if (valor[0] == "TipoAcessoGovBR") {
                    informacoes.TipoAcessoGovBR = valor[1];
                }
                else if (valor[0] == "NivelAutenticacaoGovBr") {
                    informacoes.NivelAutenticacaoGovBr = valor[1];
                }
                else if (valor[0] == "Origem") {
                    informacoes.Origem = valor[1];
                }
                else if (valor[0] == "801") {
                    informacoes._801 = valor[1];
                }

                else if (valor[0] == "-1") {
                    informacoes.Logado = false;
                }
            }
        }
    }

    return informacoes;
}

function MontarCabecalho(logado, informacoes) {

    // Mock com informacoes DadosContaGovBr
    ////informacoes = JSON.parse('{"ComCertificadoDigital":false,"ComProcuracao":false,"DadosContaGovBr":{"TipoAcessoGovBR":"passwd","NiveisAutenticacaoGovBR":[3],"SelosAutenticacaoGovBR":{"801":"certificado_digital"},"UsoDeDuploFatorDeAutenticacao":false},"HoraLogin":"/Date(1670351804897-0300)/","HoraUltimoAcesso":"/Date(1670351834177-0300)/","IDSessao":"a606515ff8f620136b26525f7aa58fd6347344c61b603735a4aac972e3ebb87c","LoginViaGovBr":true,"NI":"05033686607","NIProcurador":null,"Nome":"EDUARDO RESENDE GOMES","NomeProcurador":null,"Origem":"govbr","ThumbprintCertificado":"BACEDD641B91CDB7C4F6AABA132ED2C6AFB4ED0C","Timeout":10,"TipoNI":"PESSOA_FISICA"}');

    // Mock sem informacoes DadosContaGovBr
    ////informacoes = JSON.parse('{"ComCertificadoDigital":true,"ComProcuracao":false,"HoraLogin":"/Date(1670351804897-0300)/","HoraUltimoAcesso":"/Date(1670351834177-0300)/","IDSessao":"a606515ff8f620136b26525f7aa58fd6347344c61b603735a4aac972e3ebb87c","LoginViaGovBr":true,"NI":"05033686607","NIProcurador":null,"Nome":"EDUARDO RESENDE GOMES","NomeProcurador":null,"Origem":"govbr","ThumbprintCertificado":"BACEDD641B91CDB7C4F6AABA132ED2C6AFB4ED0C","Timeout":10,"TipoNI":"PESSOA_FISICA"}');

    if (informacoes.DadosContaGovBr != null && informacoes.DadosContaGovBr != undefined) {
        informacoes.TipoAcessoGovBR = informacoes.DadosContaGovBr.TipoAcessoGovBR;

        if (informacoes.DadosContaGovBr.NiveisAutenticacaoGovBR != null && informacoes.DadosContaGovBr.NiveisAutenticacaoGovBR != undefined)
            informacoes.NivelAutenticacaoGovBr = Math.max(informacoes.DadosContaGovBr.NiveisAutenticacaoGovBR);
    }

    var urlLogin = "https://login.esocial.gov.br/";
    var urlLogout;

    if (document.URL.indexOf("esocial.desenv") != -1) {
        urlLogin = "https://login.esocial.desenv.serpro/";
    }
    else if (document.URL.indexOf("esocial.teste") != -1) {
        urlLogin = "https://login.esocial.teste.serpro/";
    }
    else if (document.URL.indexOf("esocial.val") != -1) {
        urlLogin = "https://login.esocial.val.serpro/";
    }
    else if (document.URL.indexOf("hom.esocial") != -1) {
        urlLogin = "https://login.hom.esocial.gov.br/";
    }
    else if (document.URL.indexOf("hom.esocial") != -1) {
        urlLogin = "https://login.hom.esocial.gov.br/";
    }
    else if (document.URL.indexOf("producaorestrita.esocial") != -1) {
        urlLogin = "https://login.producaorestrita.esocial.gov.br/";
    }
    else if (document.URL.indexOf("localhost") != -1) {
        urlLogin = "https://login.esocial.desenv.serpro/";
    }

    urlLogout = urlLogin + "Logout.aspx";

    if (logado) {
        informacoes.NI = informacoes.NI.replace(/\D/g, '');

        if (informacoes.TipoNI == "PESSOA_FISICA") {
            informacoes.NI = informacoes.NI.substr(0, 3) + "." + informacoes.NI.substr(3, 3) + "." + informacoes.NI.substr(6, 3) + "-" + informacoes.NI.substr(9, 2);
        }
        else {
            informacoes.NI = informacoes.NI.substr(0, 2) + '.' + informacoes.NI.substr(2, 3) + '.' + informacoes.NI.substr(5, 3) + '/' + informacoes.NI.substr(8, 4) + '-' + informacoes.NI.substr(12, 2);
        }

        if (informacoes.ComProcuracao) {
            informacoes.NIProcurador = informacoes.NIProcurador.replace(/\D/g, '');

            if (informacoes.TipoNIProcurador == "PESSOA_FISICA") {
                informacoes.NIProcurador = informacoes.NIProcurador.substr(0, 3) + "." + informacoes.NIProcurador.substr(3, 3) + "." + informacoes.NIProcurador.substr(6, 3) + "-" + informacoes.NIProcurador.substr(9, 2);
            }
            else {
                informacoes.NIProcurador = informacoes.NIProcurador.substr(0, 2) + '.' + informacoes.NIProcurador.substr(2, 3) + '.' + informacoes.NIProcurador.substr(5, 3) + '/' + informacoes.NIProcurador.substr(8, 4) + '-' + informacoes.NIProcurador.substr(12, 2);
            }
        }

        if (informacoes.Nome.length > 120) {
            informacoes.Nome = informacoes.Nome.substring(0, 114) + " (...)";
        }
    }
    else if (document.URL.indexOf("localhost") != -1) {
        if (window['identidadeLocal'] != undefined) {
            informacoes.NI = identidadeLocal;
            informacoes.Nome = nomeUsuario;
        }
    }

    var baseUrl = $('#HiddenCurrentUrl').val();
    if (baseUrl == "//") {
        baseUrl = "/";
    }

    var labelTipoLogin = "Titular do Código";
    var trocarPerfil = '';

    if ($('#ehCodigoAcesso').length > 0 && $('#ehCodigoAcesso').val().toLowerCase() != 'true') {
        labelTipoLogin = "Titular do Certificado";
    }

    if (logado && (informacoes.ComProcuracao || informacoes.Controlador || informacoes.RepresentanteLegal || informacoes.JudiciarioOperador)) {
        labelTipoLogin = "Empregador";
    }

    // Controle de habilitação para trocar perfil
    if ($('#ExibirTrocarPerfil').length > 0 && $('#ExibirTrocarPerfil').val().toLowerCase() == 'true') {
        trocarPerfil = '<div class="separador-acoes-usuario"></div><a class="alterar-perfil" href="javascript:void(0)" onclick="location.href = MontaCaminhoCompleto(\'/Home/Index?trocarPerfil=true\')">Trocar Perfil/Módulo</a>';
    }

    var cabecalho = "<a href='" + baseUrl + "Home/Inicial' id='hplMarca' class='hide-text marca'>eSocial</a> " +
        "<input id='tipoNiEmpregador' type='hidden' value='" + informacoes.TipoNI + "'/>" +
        "<div class='identificacao-modulo'></div>" +
        "<div class='informacoes'>" +
        //TODO: Mobile
        "<button class='hidden-md hidden-lg btn-toggle-user' onclick='toggleUserMobile();'></button>";
    //if (logado && informacoes.ComCertificadoDigital) {

    if (logado) {
        if (informacoes.ComProcuracao) {
            cabecalho += '<p class="usuario"><span class="tipo-perfil-usuario">' + labelTipoLogin + ': </span><span class="numero-inscricao">' + informacoes.NI + ' - </span><span class="nome">' + informacoes.Nome + '</span></p>';
            cabecalho += '<p class="usuario"><span class="tipo-perfil-usuario">Usuário (Procurador): </span><span class="numero-inscricao">' + informacoes.NIProcurador + ' - </span><span class="nome">' + informacoes.NomeProcurador + '</span></p>';
        } else if (informacoes.Controlador) {
            cabecalho += '<p class="usuario"><span class="tipo-perfil-usuario">' + labelTipoLogin + ': </span><span class="numero-inscricao">' + informacoes.NI + ' - </span><span class="nome">' + informacoes.Nome + '</span></p>';
            cabecalho += '<p class="usuario"><span class="tipo-perfil-usuario">Usuário (Atendente): </span><span class="numero-inscricao">' + informacoes.NIControlador + ' - </span><span class="nome">' + informacoes.NomeControlador + '</span></p>';
        } else if (informacoes.JudiciarioOperador) {
            cabecalho += '<p class="usuario"><span class="tipo-perfil-usuario">' + labelTipoLogin + ': </span><span class="numero-inscricao">' + informacoes.NI + ' - </span><span class="nome">' + informacoes.Nome + '</span></p>';
            cabecalho += '<p class="usuario"><span class="tipo-perfil-usuario">Usuário (Judiciário-Operador): </span><span class="numero-inscricao">' + informacoes.NIJudiciarioOperador + ' - </span><span class="nome">' + informacoes.NomeJudiciarioOperador + '</span></p>';
            cabecalho += '<p class="usuario"><span class="tipo-perfil-usuario">Processo Judicial: </span><span class="numero-processo">' + informacoes.NumeroProcessoJudiciarioOperador + '</span></p>';
        } else if (informacoes.RepresentanteLegal) {
            cabecalho += '<p class="usuario"><span class="tipo-perfil-usuario">' + labelTipoLogin + ': </span><span class="numero-inscricao">' + informacoes.NI + ' - </span><span class="nome">' + informacoes.Nome + '</span></p>';
            cabecalho += '<p class="usuario"><span class="tipo-perfil-usuario">Usuário (Representante Legal): </span><span class="numero-inscricao">' + informacoes.NIRepresentante + ' - </span><span class="nome">' + informacoes.NomeRepresentante + '</span></p>';
        } else {
            cabecalho += "<p class='titular-certificado'>" + labelTipoLogin + "</p>";
            cabecalho += '<p class="usuario"><span class="numero-inscricao">' + informacoes.NI + ' - </span><span class="nome">' + informacoes.Nome + '</span></p>';
        }
    } else if (document.URL.indexOf("localhost") != -1) {
        cabecalho += "<p class='titular-certificado'>" + labelTipoLogin + "</p>";
        cabecalho += '<p class="usuario"><span class="numero-inscricao">' + informacoes.NI + ' - </span><span class="nome">' + informacoes.Nome + '</span></p>';
    }

    cabecalho += trocarPerfil + "</div>";

    // TODO: Mobile
    // Botao Sair para o mobile
    cabecalho += '<div class="hidden-md hidden-lg mobile-botao-sair"><a href="javascript:void(0)" id="sairAplicacao" onclick="AbrirDialogSair();">SAIR</a></div> ';

    cabecalho += "  </div> " +
        "</div> " +
        "<div class='grafismo deslogado'></div> " +
        "<div class='tempo-sessao countdown'></div> " +
        // TODO: Mobile
        "<div class='hidden-xs hidden-sm botao-sair'> " +
        //"<div class='botao-sair'> " +
        "  <a href='#' id='sairAplicacao' onclick='AbrirDialogSair();'>SAIR</a> " +
        "</div> " +
        "<a href='" + urlLogin + "' class='botao-login hide-text'>Login</a> ";

    if ($('#EhDomestico').length > 0 && $('#EhDomestico').val().toLowerCase() == 'true') {
        if (document.URL.indexOf("Home") != -1) {
            cabecalho += "<div class='hidden-xs hidden-sm botao-microphone'> " +
                //"<div class='botao-microphone'> " +
                " <br/> <a href='#' id='abrirMicrophone' onclick=' runSpeechRecognition(0);'>&nbsp;</a> " +
                "</div> ";
            "</div> ";
        }
    }


    var modalSair = "<div class='modal-sair hide fade' id='sair' data-backdrop='static' data-keyboard='false'>" +
        "	<div class='modal-body'>" +
        "		<p>Tem certeza que deseja sair?</p>" +
        "	</div>" +
        "	<div class='modal-footer'>" +
        "		<a href='#' class='btn btn-cancelar' onclick='FecharModalHeader(&#39;#sair&#39;);'>Não</a>" +
        "		<a href='" + urlLogout + "' class='btn btn-primary'>Sim</a>" +
        "	</div>" +
        "</div>";

    $("#header").html(cabecalho);
    $("#header").after(modalSair);

    document.cookie = "usuario_logado_ws=" + informacoes.NI + "; expires=0; path=/";

    if (logado || document.URL.indexOf("localhost") != -1) {
        $('#header .botao-login').hide();

        // A variável tempoSessaoExpirada está definida em _CabecalhoRodape.cshtml
        if (typeof tempoSessaoExpirada != 'undefined') {
            // A variável tempoAvisoSessaoQuaseExpirada está definida em _CabecalhoRodape.cshtml
            if (typeof tempoAvisoSessaoQuaseExpirada != 'undefined') {
                IniciaTimerSessao(tempoSessaoExpirada, tempoAvisoSessaoQuaseExpirada);
            }
            else {
                IniciaTimerSessao(tempoSessaoExpirada);
            }
        }

        $('#header .informacoes').show();
        $('#header .tempo-sessao').show();
        $('#header .botao-sair a').show();
        $('#header .botao-microphone a').show();
    }

    preencherIdentificacaoModulo();
}

function iniciarMonitoracaoSessaoExpirada(timeout) {
    var timeoutSegundos = timeout * 60;
    var duration = moment.duration(timeoutSegundos, 'seconds');
    var interval = 1000;

    if (window.idIntervalo != undefined) {
        window.clearInterval(window.idIntervalo);
    }

    window.idIntervalo = setInterval(function () {
        if (duration.asSeconds() <= 0) {
            clearInterval(window.idIntervalo);
            $('.countdown').text("Sessão expirada");

            $("#dialog-sessao-expirou").dialog(
                {
                    appendTo: 'body',
                    dialogClass: 'modal',
                    draggable: false,
                    resizable: false,
                    width: '60%',
                    title: 'Sessão expirada',
                    modal: true, open: function () { $(".ui-dialog").scrollTop("0"); },
                    buttons: [
                        {
                            text: "Continuar",
                            "id": 'btnContinuarAdiantamento',
                            "class": 'btn btn-primary',
                            click: function () {
                                RetornaCaminho("Login/Logout")
                            }
                        }]
                });
        }
        else {
            duration = moment.duration(duration.asSeconds() - 1, 'seconds');
            var text = (duration.hours() > 0) ? (duration.hours() < 10) ? '0' + duration.hours() + ':' : duration.hours() + ':' : '';
            text += (duration.minutes() > 0) ? (duration.minutes() < 10) ? '0' + duration.minutes() + ':' : duration.minutes() + ':' : '00:';
            text += (duration.seconds() > 0) ? (duration.seconds() < 10) ? '0' + duration.seconds() : duration.seconds() : '00';
            $('.countdown').text(text);
            $('.countdown').fadeIn('slow');
        }
    }, interval);
}

function iniciarMonitoracaoAvisoSessaoQuaseExpirada(timeout, tempoAvisoSessaoQuaseExpirada) {
    // Definição da modal de renovação da sessão
    var msgRenovacaoSessao = $('#dialog-sessao-quase-expirando .alert-info p').text().replace('{0}', timeout - tempoAvisoSessaoQuaseExpirada);

    if (window.idTimeoutRenovacaoSessao != undefined) {
        window.clearInterval(window.idTimeoutRenovacaoSessao);
    }

    window.idTimeoutRenovacaoSessao = setTimeout(function () {
        $('#dialog-sessao-quase-expirando .alert-info p').text(msgRenovacaoSessao);

        $('#dialog-sessao-quase-expirando').dialog(
            {
                appendTo: 'body',
                dialogClass: 'modal',
                draggable: false,
                resizable: false,
                width: '60%',
                title: 'Renovação de sessão',
                modal: true, open: function () { $(".ui-dialog").scrollTop("0"); },
                buttons: [
                    {
                        text: "OK",
                        "id": 'btnRenovarSessao',
                        "class": 'btn btn-primary',
                        click: function () {
                            clearInterval(window.idIntervalo);
                            iniciarMonitoracaoSessaoExpirada(timeout);
                            iniciarMonitoracaoAvisoSessaoQuaseExpirada(timeout, tempoAvisoSessaoQuaseExpirada);

                            AjaxCall(null, "Login/ManterSessaoAtiva", null, "Erro na chamada para manter sessão ativa.", null);

                            $(this).dialog("close");
                        }
                    },
                    {
                        text: "Cancelar",
                        "id": 'btnCancelarRenovacaoSessao',
                        "class": 'btn btn-primary btn-cancelar',
                        click: function () {
                            $(this).dialog("close");
                        }
                    }]
            });
    }, (tempoAvisoSessaoQuaseExpirada) * 60 * 1000);
}

function IniciaTimerSessao(timeout, tempoAvisoSessaoQuaseExpirada) {
    iniciarMonitoracaoSessaoExpirada(timeout);

    if (typeof tempoAvisoSessaoQuaseExpirada != 'undefined' && tempoAvisoSessaoQuaseExpirada < timeout) {
        iniciarMonitoracaoAvisoSessaoQuaseExpirada(timeout, tempoAvisoSessaoQuaseExpirada);
    }
}

function AbrirModalHeader(id, width, width_px) {
    //var modalWidth = !width ? (!width_px ? $(window).width() * 0.7 : width_px) : $(window).width() * (width / 100);

    $(id).modal('show').css({
        //'width': modalWidth,
        //'margin-left': -(modalWidth / 2),
        //'top': 100 + window.pageYOffset
        //'margin-top': function () { return $(this).height() >= $(window).height() ? window.pageYOffset + $(window).height() * 0.05 : window.pageYOffset - ($(this).height() / 2); }
    });
}

function FecharModalHeader(id) {
    $(id).modal('hide');

    if ($('.modal-backdrop').hasClass('in')) {
        $('.modal-backdrop').remove();
    }
}

function adequarLarguraItensMenuPrincipal() {
    $('#menuEmpregador').parent().find('a').width(215);
    $('#menuEmpregado.domestico').parent().find('a').width(170);
    $('#menuEmpregado.geral').parent().find('a').width(140);
    $('#menuFolhaPagamento').parent().find('a').width(187);
    $('#menuAjuda').parent().find('a').width(137);
    $('#menuFolhaPagamentoSE').parent().find('a').width(420);

    // Tratamento específico para os filhos do submenu Tabelas
    $('#menuTabelas').parent().find('a:not([id="menuTabelas"])').width(150);

    $('#menuTrabSemVinc').parent().find('a').width(210);

    // Tratamento específico para os filhos do submenu Totalizadores
    $('#menuTotalizadores').parent().find('a:not([id="menuTotalizadores"])').width(110);
    $('#menuTotalizadoresEmpregador, #menuTotalizadoresTrabalhador').css('width', 'auto');
    //$('#menuTotalizadoresEmpregador').parent().find('a:not([id="menuTotalizadoresEmpregador"])').width(160);
    //$('#menuTotalizadoresTrabalhador').parent().find('a:not([id="menuTotalizadoresTrabalhador"])').width(160);
}

function preencherIdentificacaoModulo() {
    if ($('#IdentificacaoModulo').length > 0) {
        $('#header .identificacao-modulo').text($('#IdentificacaoModulo').val());
    }
}

function getCookie(cname) {
    let name = cname + "=";
    let decodedCookie = decodeURIComponent(document.cookie);
    let ca = decodedCookie.split(';');
    for (let i = 0; i < ca.length; i++) {
        let c = ca[i];
        while (c.charAt(0) == ' ') {
            c = c.substring(1);
        }
        if (c.indexOf(name) == 0) {
            return c.substring(name.length, c.length);
        }
    }
    return "";
};
