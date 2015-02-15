UISearch = new UISearch( document.getElementById( 'sb-search' ) );

var overlay = document.getElementsByClassName("item-modal-overlay")[0];
var modal = document.getElementsByClassName("item-modal")[0];
var current_modal = null;

var container = document.querySelector('#masonry_container');
var msnry = new Masonry(container, {
    // options
    columnWidth: 300,
    itemSelector: '.item',

    gutter: 10,
    isFitWidth: true,
});

add_new_note = function() {
    var newitem = document.createElement('div');
    newitem.className = 'item shadow item-white';
    newitem.id = 'new';
    newitem.value = 'new';
    newitem.innerHTML = [
    '<div contenteditable="true" spellcheck="false" class="headline" data-placeholder="Add Title..."></div>',
    '<div contenteditable="true" spellcheck="false" class="text" data-placeholder="New Note..."></div>',
    '<div class="footer"></div>'].join('\n');
    container.insertBefore(newitem, container.firstChild);
    msnry.prepended([newitem]);
    msnry.layout();

    var text_elem = document.getElementById("new").getElementsByClassName("text")[0];
    var title_elem = document.getElementById("new").getElementsByClassName("headline")[0];
    text_elem.addEventListener('keydown', handle_keydown);
    text_elem.addEventListener('input', handle_keydown);
    title_elem.addEventListener('keydown', handle_keydown);
    title_elem.addEventListener('input', handle_keydown);
}

handle_keydown = function(e) {
    // handles showing the placeholder or nor
    if (this.textContent) {
        this.dataset.divPlaceholderContent = 'true';
    } else {
        delete(this.dataset.divPlaceholderContent);
    }

    if (this.textContent) {
        this.setAttribute('data-div-placeholder-content', 'true');
    } else {
        this.removeAttribute('data-div-placeholder-content');
    }
    
    if (!this.parentNode.value) {
        this.parentNode.value = this.parentNode.id;
    }
    
    
    // ON CTRL+SHIFT 1, 2, 3, 4, 5
    if (e.ctrlKey && e.shiftKey && e.keyCode > 48 && e.keyCode < 55) {
        classie.remove(this.parentNode, "item-orange")
        classie.remove(this.parentNode, "item-yellow");
        classie.remove(this.parentNode, "item-light-green")
        classie.remove(this.parentNode, "item-green")
        classie.remove(this.parentNode, "item-dark-green")
        classie.remove(this.parentNode, "item-white")
        if (e.keyCode == 49) classie.add(this.parentNode, "item-orange");
        if (e.keyCode == 50) classie.add(this.parentNode, "item-yellow");
        if (e.keyCode == 51) classie.add(this.parentNode, "item-light-green");
        if (e.keyCode == 52) classie.add(this.parentNode, "item-green");
        if (e.keyCode == 53) classie.add(this.parentNode, "item-dark-green");
        if (e.keyCode == 54) classie.add(this.parentNode, "item-white");
        save_item(this);
    }

    // if showing, get out
    if (e.keyCode == 27 && classie.has(overlay, "item-modal-overlay-show")) {
        modal_off(modal.getElementsByClassName("text")[0]);
    }

    // ON SHIFT-ENTER
    if (e.shiftKey && e.keyCode == 13) {
        if (classie.has(overlay, "item-modal-overlay-show")) {
            modal_off(this);
            save_item(this);
        } else {
            modal_on(this);
        }
    // DON'T DO SHIFT ENTER SAVE AND THEN AGAIN
    } else if (e.keyCode == 13 || e.type == "onblur") {
        save_item(this);
    }
};

modal_off = function(elem) {
    classie.remove(overlay, "item-modal-overlay-show");
    modal.getElementsByClassName("text")[0].removeEventListener('keydown', handle_keydown);
    modal.getElementsByClassName("text")[0].removeEventListener('input', handle_keydown);
    modal.getElementsByClassName("headline")[0].removeEventListener('keydown', handle_keydown);
    modal.getElementsByClassName("headline")[0].removeEventListener('input', handle_keydown);
    
    save_item(elem);

    // transfer changes back to original modal
    current_modal.innerHTML = modal.innerHTML;
    classie.remove(modal, "item-modal");
    current_modal.className = modal.className;
    classie.remove(modal, "item-orange")
    classie.remove(modal, "item-yellow");
    classie.remove(modal, "item-light-green")
    classie.remove(modal, "item-green")
    classie.remove(modal, "item-dark-green")

    // reset the event listerers
    current_modal.getElementsByClassName("text")[0].addEventListener('input', handle_keydown);
    current_modal.getElementsByClassName("text")[0].addEventListener('keydown', handle_keydown);
    current_modal.getElementsByClassName("headline")[0].addEventListener('keydown', handle_keydown);
    current_modal.getElementsByClassName("headline")[0].addEventListener('input', handle_keydown);

    // reset
    current_modal = null;
    modal.innerHTML = "";
    modal.className = "item-modal";
    modal.value = null;

}

modal_on = function(elem) {
    classie.add(overlay, "item-modal-overlay-show");
    
    current_modal = elem.parentNode;
    modal.className = "item-modal " + elem.parentNode.className;
    classie.remove(modal, "shadow");
    modal.innerHTML = elem.parentNode.innerHTML;
    modal.value = elem.parentNode.value;
    modal.parentNode.addEventListener("click", modal_off)


    modal.getElementsByClassName("text")[0].addEventListener('keydown', handle_keydown);
    modal.getElementsByClassName("text")[0].addEventListener('input', handle_keydown);
    modal.getElementsByClassName("headline")[0].addEventListener('keydown', handle_keydown);
    modal.getElementsByClassName("headline")[0].addEventListener('input', handle_keydown);

    modal.addEventListener("onmouseleave", function() {
        console.log("success");
        modal_off(modal.getElementsByClassName("headline")[0]);
    })
    modal.getElementsByClassName("text")[0].focus();
}

save_item = function(elem) {
    console.log('saving...');
    if(elem.className.indexOf("headline") > 0) {
        // no new lines for titles
        e.preventDefault();
    } else {
        // refresh the layout for the enter that you just pushed
        msnry.layout();
    }

    var isnew = ((elem.parentNode.value == "new") ? true : false);
    var text = elem.parentNode.getElementsByClassName("text")[0].innerText;
    var title = elem.parentNode.getElementsByClassName("headline")[0].textContent;
    var url = elem.parentNode.getElementsByClassName("headline")[0].href;
    var image = elem.parentNode.getElementsByClassName("image");
    var color = elem.parentNode.className.split(" ").slice(-1)[0];
    console.log(elem.parentNode.className.split(" ").slice(-1)[0]);
    console.log(elem.parentNode.value);
    console.log(text);
    var data = {
        data: JSON.stringify({
                id:         elem.parentNode.value,
                url:        url == undefined ? '' : url,
                image:      image.length == 0 ? '' : image[0].src,
                new_note:   isnew,
                new_group:  isnew,
                title:      title,
                content:    text,
                color:      color,
            })
    };

    $.ajax({
        url:"/update_note",
        type: 'POST',
        dataType: "json",
        data: data,
        success : function(data) {
            if(isnew) {
                elem.parentNode.id      = data.filename;
                elem.parentNode.value   = data.filename;
                add_new_note();
                msnry.layout();
            } else {
                // just update
            }

        }
    });
}


// helper for div to show "Add Notes"
// (function ($) { $('div[data-placeholder]').on('keydown keypress input', function(e) {
var elems = document.querySelectorAll('div[data-placeholder]');
for( var i=0;i<elems.length;i++) {
    elems[i].addEventListener('keydown', handle_keydown);
    elems[i].addEventListener('input', handle_keydown);
    elems[i].setAttribute('data-div-placeholder-content', 'true');
}

setTimeout(function() { 
    UISearch.open();
    add_new_note();
}, 200);
