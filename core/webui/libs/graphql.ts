import logger from "./logger";


function isObject(obj:any) {
    return obj === Object(obj);
}

export function gql(strings:any): string {
    return strings.raw[0];
}

export function toModel (gql: any) {
    if (gql == null) {
        return null;
    } else if(gql.data === undefined) {
        if (gql.formats) return gql.formats; // image formats
        if (gql.thumbnail) return gql.thumbnail; // image thumbnail
        logger.debug(gql)
        throw 'GraphQL data is undefined';
    } else if(gql.data == null) {
        return null;
    } else if (Array.isArray(gql.data)) {
        let data:any = [];
        gql.data.forEach((el:any) => {
            data.push(toModel({data:el}));
        });
        return data;
    } else if (isObject(gql.data)) {// object
        let data:any = {}
        if(gql.data.id) data['id'] = gql.data.id;
        if(gql.data.attributes) {
            for (const [key, value] of Object.entries(gql.data.attributes)) {
                if(isObject(gql.data.attributes[key])) {
                    data[key] = toModel(gql.data.attributes[key]);
                } else {
                    data[key] = gql.data.attributes[key];
                }
            }
        } else {
            throw 'GraphQL data has no attributes'
        }
        return data;
    } else {
        throw 'GraphQL gql.data is not object or array'
    }
};
