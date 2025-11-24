from typing import Any, Dict, List, Optional
import os
import requests
import logging
import json as _json
import time

# fal_client может отсутствовать в окружении контейнера; делаем импорт опциональным
try:
	import fal_client  # type: ignore
except ImportError:
	fal_client = None  # type: ignore

from app.core.config import settings

# Утилиты S3 (пресайн ссылок)
from app.services.s3_utils import parse_s3_url, get_file_url_with_expiry


logger = logging.getLogger("livephoto.fal")

# Ensure API key is set for fal_client
if settings.fal_key:
	os.environ.setdefault("FAL_KEY", settings.fal_key)


def upload_file_and_generate(image_path: str, prompt: str, sync_mode: bool = True) -> Dict[str, Any]:
	if fal_client is None:
		raise RuntimeError("fal-client не установлен в контейнере. Установите 'fal-client' или используйте submit_generation (HTTP queue API).")
	logger.info(f"fal.sdk upload_file path={image_path}")
	# fal_client.upload_file ожидает локальный путь к файлу; не подменяем на S3 URL
	uploaded_url = fal_client.upload_file(image_path)
	logger.info(f"fal.sdk upload_file -> url={uploaded_url}")
	logger.info(f"fal.sdk subscribe model={settings.fal_endpoint} args={{'prompt': <len={len(prompt)}>, 'image_url': '<uploaded>', 'sync_mode': {sync_mode}}}")
	result = fal_client.subscribe(
		settings.fal_endpoint,
		arguments={
			"prompt": prompt,
			"image_url": uploaded_url,
			"sync_mode": sync_mode,
		},
		with_logs=True,
	)
	logger.info(f"fal.sdk subscribe -> result={_json.dumps(result)[:2000]}")
	return result


def generate_multiple(image_paths: List[str], prompts: List[str] | None = None, sync_mode: bool = True) -> List[Dict[str, Any]]:
	results: List[Dict[str, Any]] = []
	for idx, path in enumerate(image_paths):
		prompt = prompts[idx] if prompts and idx < len(prompts) else "Animate this image"
		results.append(upload_file_and_generate(path, prompt=prompt, sync_mode=sync_mode))
	return results


def generate_from_url(image_url: str, prompt: str, sync_mode: bool = True) -> Dict[str, Any]:
	"""Генерация по внешнему URL изображения (presigned S3)."""
	if fal_client is None:
		raise RuntimeError("fal-client не установлен в контейнере. Установите 'fal-client' или используйте submit_generation (HTTP queue API).")
	# Если передан s3:// — преобразуем в публичный presigned URL
	if image_url.startswith("s3://"):
		b, k = parse_s3_url(image_url)
		image_url, _ = get_file_url_with_expiry(b, k)
	logger.info(f"fal.sdk subscribe model={settings.fal_endpoint} args={{'prompt': <len={len(prompt)}>, 'image_url': '<url>', 'sync_mode': {sync_mode}}}")
	result = fal_client.subscribe(
		settings.fal_endpoint,
		arguments={
			"prompt": prompt,
			"image_url": image_url,
			"sync_mode": sync_mode,
		},
		with_logs=True,
	)
	logger.info(f"fal.sdk subscribe -> result={_json.dumps(result)[:2000]}")
	return result


def submit_generation(
    image_url: Optional[str],
    prompt: str,
    order_id: str,
    item_index: int,
    anon_user_id: str | None = None,
    endpoint: str | None = None,
    extra_args: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
	"""Поставить задачу в очередь fal.ai с вебхуком и вернуть request_id.

	Идемпотентность обеспечиваем на уровне нашего заказа (не запускаем повторно, если есть request_id).
	"""
	# Вариант без вебхука: статус будет обновляться только поллером

	# Входные параметры (безопасное логирование)
	try:
		img_kind = "s3" if image_url and image_url.startswith("s3://") else ("http" if image_url else "none")
		logger.info(
			f"submit_generation: called image_url={img_kind} prompt_len={len(prompt) if isinstance(prompt, str) else 0} "
			f"order_id={order_id} item_index={item_index} anon_user_id={'set' if anon_user_id else 'none'} "
			f"endpoint_override={(endpoint or 'none')} extra_args_keys={list((extra_args or {}).keys())[:20]}"
		)
	except Exception:
		logger.exception("submit_generation: failed to log call arguments")

	start_ts = time.perf_counter()

	# Убедимся, что image_url публичный (presigned), если пришёл как s3://
	try:
		if image_url and image_url.startswith("s3://"):
			logger.info("submit_generation: presign S3 image url start")
			b, k = parse_s3_url(image_url)
			logger.info(f"submit_generation: parsed s3 bucket={b} key={k}")
			image_url, _ = get_file_url_with_expiry(b, k)
			logger.info(f"submit_generation: presign result scheme={'s3' if image_url.startswith('s3://') else 'http(s)'}")
			if image_url.startswith("s3://"):
				# если по какой-то причине не преобразовалось — явно падаем
				raise ValueError("submit_generation: failed to presign s3 image url")
	except Exception:
		logger.exception("submit_generation: error while presigning image_url")
		raise

	# Используем официальный fal-client для постановки в очередь
	if fal_client is None:
		logger.error("submit_generation: fal_client is None; cannot submit")
		raise RuntimeError("fal-client не установлен в контейнере. Установите 'fal-client'.")
	use_endpoint = endpoint or settings.fal_endpoint
	logger.info(f"submit_generation: using endpoint {use_endpoint}")
	arguments: Dict[str, Any] = {}
	# Передаём prompt только если он задан
	if isinstance(prompt, str) and prompt != "":
		arguments["prompt"] = prompt
	# Добавляем image_url только если он действительно задан
	if image_url:
		arguments["image_url"] = image_url
	# Дополнительные аргументы модели (например, для реставрации фото)
	if extra_args:
		for k, v in extra_args.items():
			if k in ("prompt", "image_url"):
				continue
			arguments[k] = v
	mask_arguments = dict(arguments)
	if "image_url" in mask_arguments:
		mask_arguments["image_url"] = "<https>"
	if "prompt" in mask_arguments:
		try:
			mask_arguments["prompt"] = f"<len={len(str(mask_arguments['prompt']))}>"
		except Exception:
			mask_arguments["prompt"] = "<len=? >"
	logger.info(
		f"fal.sdk submit model={use_endpoint} args={_json.dumps(mask_arguments)[:2000]}"
	)
	try:
		submit_ts = time.perf_counter()
		handler = fal_client.submit(use_endpoint, arguments=arguments)
		elapsed_ms = int((time.perf_counter() - submit_ts) * 1000)
		# Снимем безопасные поля из handler (если есть)
		safe_info: Dict[str, Any] = {}
		for attr in ("request_id", "status", "response_url", "queue_position"):
			try:
				val = getattr(handler, attr, None)
				if val is not None:
					safe_info[attr] = val
			except Exception:
				continue
		handler_type = getattr(handler, "__class__", type(handler)).__name__
		logger.info(f"fal.sdk submit -> elapsed_ms={elapsed_ms} handler_type={handler_type} info={safe_info}")
	except Exception:
		logger.exception("submit_generation: fal_client.submit raised")
		raise
	request_id = getattr(handler, "request_id", None)
	if not request_id:
		try:
			handler_type = getattr(handler, "__class__", type(handler)).__name__
			handler_repr = str(handler)
		except Exception:
			handler_type = handler_type if 'handler_type' in locals() else "<unknown>"
			handler_repr = "<unrepr>"
		logger.error(f"fal-client: request_id not returned by submit; handler_type={handler_type} handler_repr={handler_repr[:1000]}")
		raise ValueError("fal-client: request_id not returned by submit")
	total_ms = int((time.perf_counter() - start_ts) * 1000)
	logger.info(f"submit_generation: return request_id={request_id} model_id={use_endpoint} total_ms={total_ms}")
	return {"request_id": request_id, "model_id": use_endpoint}


def get_request_status(request_id: str, logs: bool = False, model_id: str | None = None) -> Dict[str, Any]:
	"""Получить статус задачи через fal-client по ПОЛНОМУ пути модели."""
	if fal_client is None:
		raise RuntimeError("fal-client не установлен в контейнере. Установите 'fal-client'.")
	model_path = model_id or settings.fal_endpoint
	logger.info(
		f"fal.sdk status model={model_path} request_id={request_id} with_logs={logs}"
	)
	data = fal_client.status(model_path, request_id, with_logs=logs)
	# Безопасное логирование (fal-client может возвращать несериализуемые объекты, напр. InProgress)
	try:
		log_str = _json.dumps(data)[:2000]  # type: ignore[arg-type]
	except TypeError:
		log_str = str(data)
	logger.info(f"fal.sdk status -> {log_str}")
	# Нормализуем в dict, чтобы вызывающий код не падал на .get
	if isinstance(data, dict):
		return data
	# Объект fal_client.* — попытаемся извлечь статус
	try:
		status_val = getattr(data, "status", None)
		if isinstance(status_val, str) and status_val:
			status_norm = status_val.upper()
		else:
			cls_name = data.__class__.__name__.upper()
			if "COMPLETED" in cls_name:
				status_norm = "COMPLETED"
			elif "INPROGRESS" in cls_name or "IN_PROGRESS" in cls_name:
				status_norm = "IN_PROGRESS"
			elif "FAILED" in cls_name or "ERROR" in cls_name:
				status_norm = "FAILED"
			elif "CANCELLED" in cls_name or "CANCELED" in cls_name:
				status_norm = "CANCELLED"
			else:
				status_norm = "IN_PROGRESS"
	except Exception:
		status_norm = "IN_PROGRESS"
	# Соберём полезные поля если есть
	resp = {"status": status_norm}
	for fld in ("logs", "metrics", "response_url"):
		try:
			val = getattr(data, fld, None)
			if val is not None:
				resp[fld] = val
		except Exception:
			continue
	return resp


def get_request_response(request_id: str, model_id: str | None = None) -> Dict[str, Any]:
	"""Получить результат задачи через fal-client по ПОЛНОМУ пути модели."""
	if fal_client is None:
		raise RuntimeError("fal-client не установлен в контейнере. Установите 'fal-client'.")
	model_path = model_id or settings.fal_endpoint
	logger.info(
		f"fal.sdk result model={model_path} request_id={request_id}"
	)
	data = fal_client.result(model_path, request_id)
	try:
		log_str = _json.dumps(data)[:2000]
	except TypeError:
		log_str = str(data)
	logger.info(f"fal.sdk result -> {log_str}")
	# На практике result возвращает dict; если иное — приведём к строковому виду
	if isinstance(data, dict):
		return data
	return {"response": str(data)}


def extract_media_url(payload: Dict[str, Any]) -> Optional[str]:
	"""Пытается извлечь URL видео из ответа fal (учитывая разные модели/форматы).

	Возвращает первую найденную строку, похожую на URL, обходя популярные поля и структуры.
	"""
	def _pick_from_dict(data: Dict[str, Any]) -> Optional[str]:
		# Прямые кандидаты
		for k in ("video_url", "url", "response_url"):
			v = data.get(k)
			if isinstance(v, str) and v:
				return v
		# Популярные вложенные объекты
		for nk in ("video", "output", "result", "data", "media"):
			v = data.get(nk)
			if isinstance(v, dict):
				u = _pick_from_dict(v)
				if u:
					return u
			elif isinstance(v, list):
				for it in v:
					if isinstance(it, dict):
						u = _pick_from_dict(it)
						if u:
							return u
					elif isinstance(it, str) and it:
						return it
		# Массивы выходов (добавили images для фото-моделей)
		for ak in ("videos", "outputs", "files", "images"):
			arr = data.get(ak)
			if isinstance(arr, list):
				for it in arr:
					if isinstance(it, dict):
						u = _pick_from_dict(it)
						if u:
							return u
					elif isinstance(it, str) and it:
						return it
		return None

	root = payload or {}
	# Часто всё лежит в response
	resp_obj = root.get("response") if isinstance(root, dict) else None
	if isinstance(resp_obj, dict):
		u = _pick_from_dict(resp_obj)
		if u:
			logger.info(f"fal.util extract_media_url -> {u}")
			return u
	# Пробуем на верхнем уровне
	if isinstance(root, dict):
		u = _pick_from_dict(root)
		if u:
			logger.info(f"fal.util extract_media_url -> {u}")
			return u
	return None


def fetch_queue_json(url: str) -> Dict[str, Any]:
	"""Авторизованный GET к queue.fal.run с логированием тела ответа."""
	headers = {"Authorization": f"Key {settings.fal_key}"}
	logger.info(f"fal.http GET {url} headers={{'Authorization': 'Key ****'}}")
	resp = requests.get(url, headers=headers, timeout=60)
	resp.raise_for_status()
	data = resp.json()
	logger.info(f"fal.http <- {resp.status_code} body={_json.dumps(data)[:2000]}")
	return data


def fetch_bytes(url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 180) -> bytes:
	"""GET байтов по URL с логом статуса и длины."""
	mask_headers = dict(headers or {})
	if "Authorization" in mask_headers:
		mask_headers["Authorization"] = "****"
	logger.info(f"fal.http GET {url} headers={mask_headers}")
	resp = requests.get(url, headers=headers, timeout=timeout)
	resp.raise_for_status()
	content_len = resp.headers.get("Content-Length") or len(resp.content)
	logger.info(f"fal.http <- {resp.status_code} bytes={content_len}")
	return resp.content
