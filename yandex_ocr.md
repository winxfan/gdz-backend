Vision OCR API: REST reference


The service does not operate with resources.
Interface definitions available at GitHub.
Service URL: https://ocr.api.cloud.yandex.net
Service	Description
Operation	A set of methods for managing operations for asynchronous API requests.
TextRecognitionAsync	A set of methods for managing operations for asynchronous API requests.
TextRecognition	A set of methods for the Vision OCR service.

Vision OCR API, REST: Operation

Yandex Cloud
Обновлена 17 октября 2024 г.
A set of methods for managing operations for asynchronous API requests.

Methods
Method	Description
Get	Returns the specified Operation resource.
Cancel	Cancels the specified operation.

Vision OCR API, REST: Operation.Get


Yandex Cloud
Returns the specified Operation resource.

HTTP request
GET https://operation.api.cloud.yandex.net/operations/{operationId}


Path parameters
Field	Description
operationId	string
Required field. ID of the Operation resource to return.
Response
HTTP Code: 200 - OK
{
  "id": "string",
  "description": "string",
  "createdAt": "string",
  "createdBy": "string",
  "modifiedAt": "string",
  "done": "boolean",
  "metadata": "object",
  // Includes only one of the fields `error`, `response`
  "error": {
    "code": "integer",
    "message": "string",
    "details": [
      "object"
    ]
  },
  "response": "object"
  // end of the list of possible fields
}

An Operation resource. For more information, see Operation.
	
	
Field	Description
id	string
ID of the operation.
description	string
Description of the operation. 0-256 characters long.
createdAt	string (date-time)
Creation timestamp.
String in RFC3339 text format. The range of possible values is from0001-01-01T00:00:00Z to 9999-12-31T23:59:59.999999999Z, i.e. from 0 to 9 digits for fractions of a second.
To work with values in this field, use the APIs described in theProtocol Buffers reference.In some languages, built-in datetime utilities do not support nanosecond precision (9 digits).
createdBy	string
ID of the user or service account who initiated the operation.
modifiedAt	string (date-time)
The time when the Operation resource was last modified.
String in RFC3339 text format. The range of possible values is from0001-01-01T00:00:00Z to 9999-12-31T23:59:59.999999999Z, i.e. from 0 to 9 digits for fractions of a second.
To work with values in this field, use the APIs described in theProtocol Buffers reference.In some languages, built-in datetime utilities do not support nanosecond precision (9 digits).
done	boolean
If the value is false, it means the operation is still in progress.If true, the operation is completed, and either error or response is available.
metadata	object
Service-specific metadata associated with the operation.It typically contains the ID of the target resource that the operation is performed on.Any method that returns a long-running operation should document the metadata type, if any.
Status
The error result of the operation in case of failure or cancellation.


Vision OCR API, REST: TextRecognitionAsync


Yandex Cloud
Обновлена 17 октября 2024 г.
A set of methods for managing operations for asynchronous API requests.

Methods
Method	Description
Recognize	To send the image for asynchronous text recognition.
GetRecognition	To get recognition results.

Vision OCR API, REST: TextRecognitionAsync.Recognize


Yandex Cloud
Обновлена 8 августа 2025 г.
To send the image for asynchronous text recognition.

HTTP request
POST https://ocr.api.cloud.yandex.net/ocr/v1/recognizeTextAsync


Body parameters
{
  // Includes only one of the fields `content`
  "content": "string",
  // end of the list of possible fields
  "mimeType": "string",
  "languageCodes": [
    "string"
  ],
  "model": "string"
}

Field	Description
content	string (bytes)
Bytes with data
Includes only one of the fields content.
mimeType	string
Specifications of the (MIME type). Each specification contains the file to analyze and features to use for analysis. Restrictions:
	•	Supported file formats: JPEG, PNG, PDF.
	•	Maximum file size: see documentation.
	•	Image size should not exceed 20M pixels (length x width).
	•	The number of pages in a PDF file should not exceed 1.
languageCodes[]	string
List of the languages to recognize text.Specified in ISO 639-1 format (for example, ru).
model	string
Model to use for text detection.
Response
HTTP Code: 200 - OK
{
  "id": "string",
  "description": "string",
  "createdAt": "string",
  "createdBy": "string",
  "modifiedAt": "string",
  "done": "boolean",
  "metadata": "object",
  // Includes only one of the fields `error`
  "error": {
    "code": "integer",
    "message": "string",
    "details": [
      "object"
    ]
  }
  // end of the list of possible fields
}

An Operation resource. For more information, see Operation.
An Operation resource. For more information, see Operation.
Field	Description
id	string
ID of the operation.
description	string
Description of the operation. 0-256 characters long.
createdAt	string (date-time)
Creation timestamp.
String in RFC3339 text format. The range of possible values is from0001-01-01T00:00:00Z to 9999-12-31T23:59:59.999999999Z, i.e. from 0 to 9 digits for fractions of a second.
To work with values in this field, use the APIs described in theProtocol Buffers reference.In some languages, built-in datetime utilities do not support nanosecond precision (9 digits).
createdBy	string
ID of the user or service account who initiated the operation.
modifiedAt	string (date-time)
The time when the Operation resource was last modified.
String in RFC3339 text format. The range of possible values is from0001-01-01T00:00:00Z to 9999-12-31T23:59:59.999999999Z, i.e. from 0 to 9 digits for fractions of a second.
To work with values in this field, use the APIs described in theProtocol Buffers reference.In some languages, built-in datetime utilities do not support nanosecond precision (9 digits).
done	boolean
If the value is false, it means the operation is still in progress.If true, the operation is completed, and either error or response is available.
metadata	object
Service-specific metadata associated with the operation.It typically contains the ID of the target resource that the operation is performed on.Any method that returns a long-running operation should document the metadata type, if any.
error	Status
The error result of the operation in case of failure or cancellation.
Includes only one of the fields error.
The operation result.If done == false and there was no failure detected, neither error nor response is set.If done == false and there was a failure detected, error is set.If done == true, exactly one of error or response is set.

Status
The error result of the operation in case of failure or cancellation.
Field	Description
code	integer (int32)
Error code. An enum value of google.rpc.Code.
message	string
An error message.
details[]	object
A list of messages that carry the error details.

Vision OCR API, REST: TextRecognitionAsync.GetRecognition


Yandex Cloud
Обновлена 8 августа 2025 г.
To get recognition results.

HTTP request
GET https://ocr.api.cloud.yandex.net/ocr/v1/getRecognition


Query parameters
Field	Description
operationId	string
Required field. Operation ID of async recognition request.
Response
HTTP Code: 200 - OK
{
  "textAnnotation": {
    "width": "string",
    "height": "string",
    "blocks": [
      {
        "boundingBox": {
          "vertices": [
            {
              "x": "string",
              "y": "string"
            }
          ]
        },
        "lines": [
          {
            "boundingBox": {
              "vertices": [
                {
                  "x": "string",
                  "y": "string"
                }
              ]
            },
            "text": "string",
            "words": [
              {
                "boundingBox": {
                  "vertices": [
                    {
                      "x": "string",
                      "y": "string"
                    }
                  ]
                },
                "text": "string",
                "entityIndex": "string",
                "textSegments": [
                  {
                    "startIndex": "string",
                    "length": "string"
                  }
                ]
              }
            ],
            "textSegments": [
              {
                "startIndex": "string",
                "length": "string"
              }
            ],
            "orientation": "string"
          }
        ],
        "languages": [
          {
            "languageCode": "string"
          }
        ],
        "textSegments": [
          {
            "startIndex": "string",
            "length": "string"
          }
        ],
        "layoutType": "string"
      }
    ],
    "entities": [
      {
        "name": "string",
        "text": "string"
      }
    ],
    "tables": [
      {
        "boundingBox": {
          "vertices": [
            {
              "x": "string",
              "y": "string"
            }
          ]
        },
        "rowCount": "string",
        "columnCount": "string",
        "cells": [
          {
            "boundingBox": {
              "vertices": [
                {
                  "x": "string",
                  "y": "string"
                }
              ]
            },
            "rowIndex": "string",
            "columnIndex": "string",
            "columnSpan": "string",
            "rowSpan": "string",
            "text": "string",
            "textSegments": [
              {
                "startIndex": "string",
                "length": "string"
              }
            ]
          }
        ]
      }
    ],
    "fullText": "string",
    "rotate": "string",
    "markdown": "string",
    "pictures": [
      {
        "boundingBox": {
          "vertices": [
            {
              "x": "string",
              "y": "string"
            }
          ]
        },
        "score": "string"
      }
    ]
  },
  "page": "string"
}

Field	Description
textAnnotation	TextAnnotation
Recognized text blocks in page or text from entities.
page	string (int64)
Page number in PDF file.
TextAnnotation
Field	Description
width	string (int64)
Page width in pixels.
height	string (int64)
Page height in pixels.
blocks[]	Block
Recognized text blocks in this page.
entities[]	Entity
Recognized entities.
tables[]	Table
fullText	string
Full text recognized from image.
rotate	enum (Angle)
Angle of image rotation.
	•	ANGLE_UNSPECIFIED
	•	ANGLE_0
	•	ANGLE_90
	•	ANGLE_180
	•	ANGLE_270
markdown	string
Full markdown (without pictures inside) from image. Available only in markdown and math-markdown models.
pictures[]	Picture
List of pictures locations from image.

Block
Field	Description
boundingBox	Polygon
Area on the page where the text block is located.
lines[]	Line
Recognized lines in this block.
languages[]	DetectedLanguage
A list of detected languages
textSegments[]	TextSegments
Block position from full_text string.
layoutType	enum (LayoutType)
Block layout type.
	•	LAYOUT_TYPE_UNSPECIFIED
	•	LAYOUT_TYPE_UNKNOWN
	•	LAYOUT_TYPE_TEXT
	•	LAYOUT_TYPE_HEADER
	•	LAYOUT_TYPE_SECTION_HEADER
	•	LAYOUT_TYPE_FOOTER
	•	LAYOUT_TYPE_FOOTNOTE
	•	LAYOUT_TYPE_PICTURE
	•	LAYOUT_TYPE_CAPTION
	•	LAYOUT_TYPE_TITLE
	•	LAYOUT_TYPE_LIST

Polygon
Field	Description
vertices[]	Vertex
The bounding polygon vertices.

Vertex
Vertex
Field	Description
x	string (int64)
X coordinate in pixels.
y	string (int64)
Y coordinate in pixels.

Line
Field	Description
boundingBox	Polygon
Area on the page where the line is located.
text	string
Recognized text.
words[]	Word
Recognized words.
textSegments[]	TextSegments
Line position from full_text string.
orientation	enum (Angle)
Angle of line rotation.
	•	ANGLE_UNSPECIFIED
	•	ANGLE_0
	•	ANGLE_90
	•	ANGLE_180
	•	ANGLE_270

Word
Field	Description
boundingBox	Polygon
Area on the page where the word is located.
text	string
Recognized word value.
entityIndex	string (int64)
ID of the recognized word in entities array.
textSegments[]	TextSegments
Word position from full_text string.

TextSegments
Field	Description
startIndex	string (int64)
Start character position from full_text string.
length	string (int64)
Text segment length.

DetectedLanguage
Field	Description
languageCode	string
Detected language code.

Entity
Entity
Field	Description
name	string
Entity name.
text	string
Recognized entity text.

Table
Field	Description
boundingBox	Polygon
Area on the page where the table is located.
rowCount	string (int64)
Number of rows in table.
columnCount	string (int64)
Number of columns in table.
cells[]	TableCell
Table cells.

TableCell
Field	Description
boundingBox	Polygon
Area on the page where the table cell is located.
rowIndex	string (int64)
Row index.
columnIndex	string (int64)
Column index.
columnSpan	string (int64)
Column span.
rowSpan	string (int64)
Row span.
text	string
Text in cell.
textSegments[]	TextSegments
Table cell position from full_text string.

Picture
Field	Description
boundingBox	Polygon
Area on the page where the picture is located.
score	string
Confidence score of picture location.
