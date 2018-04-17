function Document(data) {
    this.content = data.content;
    this.annotations = data.annotations;
    this.types = null;

    this.getTypes = function() {
        if (this.types == null) {
            var set = {}
            this.annotations.forEach(function(a) {
                set[a.type] = true;
            });
            this.types = [];
            for (var t in set) {
                this.types.push(t);
            }
        }
        return this.types;
    }

    this.selectType = function(types) {
        var doc = new Document(this);
        doc.annotations = [];
        this.annotations.forEach(function(a) {
            if (types.indexOf(a.type) != -1) {
                doc.annotations.push(a);
            }
        });
        return doc;
    }

    this.selectContains = function(span) {
        var doc = new Document(this);
        doc.annotations = [];
        this.annotations.forEach(function(a) {
            if (a.span[0] <= span[0] && a.span[1] >= span[1]) {
                doc.annotations.push(a);
            }
        });
        return doc;
    }

    this.selectWithin = function(span) {
        var doc = new Document(this);
        doc.annotations = [];
        this.annotations.forEach(function(a) {
            if (span[0] <= a.span[0] && span[1] >= a.span[1]) {
                doc.annotations.push(a);
            }
        });
        return doc;
    }

    this.selectOverlapping = function(span) {
        var doc = new Document(this);
        doc.annotations = [];
        this.annotations.forEach(function(a) {
            if (span[0] <= a.span[0] && span[1] >= a.span[1]) {
                doc.annotations.push(a);
            } else if (a.span[0] <= span[0] && a.span[1] >= span[1]) {
                doc.annotations.push(a);
            }
        });
        return doc;
    }

    this.sortAnnotations = function() {
        this.annotations.sort(function(a, b){
            if(a.span[0] < b.span[0]) return -1;
            if(a.span[0] > b.span[0]) return 1;
            return 0;
        });
    }
}
